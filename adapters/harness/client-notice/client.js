// Dependency-free client source in Harness rc1's public module registration format.
// Keep the notification on the submitting session, never whichever session is active later.
window.__ModuleLoader__.load({
  id: 'recaloom-harness-notice',
  factory: () => ({
    name: 'recaloom-command-notice',
    inject: ['commandUi', 'sessions', 'conversation'],
    apply(ctx) {
      ctx.on('command/executed', (sessionId, name, result) => {
        if (name !== 'recaloom' || typeof result?.text !== 'string' || !result.text.trim()) return;
        if (result.kind !== 'success' && result.kind !== 'error') return;
        const origin = ctx.sessions.scope(sessionId);
        if (!origin) return;
        ctx.conversation.input.for(origin).notify(result.kind === 'error' ? 'error' : 'info', result.text);
      });
    },
  }),
});
