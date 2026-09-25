// Native DSH plugin: trusted composition binds one project; human commands control it.
import z from '@deepseek-ai/schemastery';
import { createUserMessage } from '@deepseek-ai/dsh-llm';
import { realpathSync } from 'node:fs';
import { isAbsolute } from 'node:path';
import { createHash } from 'node:crypto';
import { attachDshRecovery } from './automatic-recovery.mjs';

export const name = 'recaloom-recovery';
export const inject = ['commands', 'settings'];
export const Config = z.object({
  python: z.string().required(), recovery: z.string().required(),
  project: z.string().required(), projectId: z.string().required(),
});

export async function apply(ctx, config) {
  for (const key of ['python', 'recovery', 'project'])
    if (!isAbsolute(config[key])) throw new Error('Recaloom requires absolute installation paths');
  const project = realpathSync(config.project);
  const binding = createHash('sha256').update(JSON.stringify([project, config.projectId])).digest('hex');
  let settings;
  let writeSettings;
  let settingsRevision;
  let removing = false;
  const storageOwner = await ctx.plugin({ name: 'recaloom-settings-owner', inject: ['settings'], apply(owner) {
    settings = owner.settings.register('recaloom-recovery', z.object({
      enabled: z.boolean().default(false), binding: z.string().default(''),
    }), {
      applies: 'live',
      validate(value) {
        // Cover every public Settings write, not only our slash command.
        // SDK validation runs on the serialized write queue before persistence.
        if (removing && value.enabled) throw new Error('REMOVAL_PENDING');
      },
    });
    writeSettings = (patch, revision) => owner.settings.update('recaloom-recovery', patch, revision);
    settingsRevision = () => owner.settings.describe().find(item => item.ns === 'recaloom-recovery').revision;
  } });
  // An explicit child owns registration: draining the command queue must precede
  // unregistering it. Ordinary sibling effects unload concurrently in Cordis.
  return ctx.effect(function* () {
  yield storageOwner.dispose;
  const control = attachDshRecovery(ctx, { ...config, project }, createUserMessage, { visibleErrors: true });
  let closed = false;
  let held = false;
  let removalPending;
  let removalRevision;
  let intent = 0;
  let tail = Promise.resolve();
  const sync = () => {
    if (closed) return;
    const saved = settings.get();
    if (!removing && !held && saved.enabled && saved.binding === binding) control.resume();
    else control.pause();
  };
  sync();
  const unwatch = settings.watch(sync);
  const status = () => {
    const current = control.status();
    return `Recaloom ${current.state.toUpperCase()}\n项目: ${project}\n项目编号: ${config.projectId}\n最近恢复: ${current.lastCode}\n只读恢复；不自动保存。暂停不会抹去已进入对话的内容。`;
  };
  const belongs = agent => {
    try { return realpathSync(agent.session.header.cwd) === project; }
    catch { return false; }
  };
  const unregister = ctx.commands.register({
    name: 'recaloom', description: '项目记忆：查看状态、暂停或恢复（不调用模型）',
    input: { hint: 'status | pause | resume' }, recordInput: false,
    handler(invocation) {
      // Serialize command effects, but pause immediately fences in-flight recovery.
      const action = invocation.rawInput.trim().toLowerCase() || 'status';
      if (!belongs(invocation.agent)) return { kind: 'error', text: 'UNBOUND_PROJECT：此会话未绑定 Recaloom；未读取其他项目。' };
      if (removing) return { kind: 'error', text: 'REMOVAL_PENDING：正在准备移除；此挂载不再接受启用请求。' };
      if (!['status', 'pause', 'resume'].includes(action))
        return { kind: 'error', text: '用法：/recaloom status、/recaloom pause、/recaloom resume' };
      // Capture both user-intent order and the public settings revision NOW,
      // not later when this invocation reaches the private command queue.
      const ticket = action === 'status' ? intent : ++intent;
      const revision = settingsRevision();
      if (action === 'pause') { held = true; control.pause(); }
      const result = tail.then(async () => {
        if (closed || invocation.signal.aborted || !belongs(invocation.agent))
          return { kind: 'error', text: 'CANCELLED：操作未完成。' };
        if (action === 'status') return { kind: 'success', text: status() };
        if (ticket !== intent) return { kind: 'error', text: 'SUPERSEDED：已有更新的记忆控制操作，旧请求未执行。' };
        held = true;
        control.pause();
        try {
          await writeSettings({ enabled: action === 'resume', binding }, revision);
          if (closed || invocation.signal.aborted || ticket !== intent || !belongs(invocation.agent)) {
            // A UI cancellation can arrive after the file commit. Compensate
            // before teardown settles so a later mount does not inherit a grant.
            await writeSettings({ enabled: false, binding }, settingsRevision());
            return { kind: 'error', text: 'CANCELLED：已保持暂停，请检查状态后再恢复。' };
          }
          held = false;
          sync();
          return { kind: 'success', text: status() };
        } catch {
          // A failed write cannot reactivate the reader through a late watcher.
          return { kind: 'error', text: 'SETTINGS_WRITE_FAILED：本次保持暂停；未确认保存，请修复设置存储后再恢复。' };
        }
      });
      tail = result.catch(() => {});
      return result;
    },
  });
  // A trusted in-process supervisor can fence the command queue BEFORE stopping
  // the host. This is not a model tool, HTTP endpoint or a file-deletion grant.
  const removalStatus = () => {
    if (closed) return { state: 'disposed', readyForRemoval: false };
    const saved = settings.get();
    const ready = removing && !removalPending && removalRevision !== undefined &&
      removalRevision === settingsRevision() && saved.enabled === false && saved.binding === binding;
    return { state: ready ? 'quiesced' : removing ? 'quiescing' : 'attached', readyForRemoval: ready };
  };
  ctx.provide('recaloomLifecycle', {
    status: removalStatus,
    prepareRemoval() {
      if (closed) return Promise.reject(new Error('REMOVAL_DISPOSED'));
      if (removalPending) return removalPending;
      removing = true;
      held = true;
      ++intent;
      removalRevision = undefined;
      control.pause();
      const queued = tail;
      removalPending = queued.then(async () => {
        await control.drain();
        // A pre-existing Settings client may still be committing its activation.
        // Queue the safety pause behind it, not with a prematurely read revision.
        // Unlike resume, this monotonic disable cannot grant new read authority.
        await writeSettings({ enabled: false, binding });
        const saved = settings.get();
        if (saved.enabled !== false || saved.binding !== binding) throw new Error('REMOVAL_STATE_CHANGED');
        removalRevision = settingsRevision();
        return { state: 'quiesced', persistedEnabled: false, binding, settingsRevision: removalRevision };
      }).catch(() => {
        removalRevision = undefined;
        throw new Error('REMOVAL_PAUSE_NOT_PERSISTED');
      }).finally(() => { removalPending = undefined; });
      return removalPending;
    },
  });
  yield async () => {
    closed = true;
    control.dispose();
    unregister();
    unwatch();
    await tail;
    await control.drain();
    // Keep the namespace alive until the supervisor's final persistence settles.
    // The public prepare promise still rejects on failure. Teardown, however,
    // must finish releasing the settings owner rather than skipping it.
    if (removalPending) await Promise.allSettled([removalPending]);
  };
  }, 'Recaloom binding lifetime');
}
