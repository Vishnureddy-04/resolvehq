/* ResolveHQ service worker: shows team alerts even when the company console is closed. */
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));

self.addEventListener('push', event => {
  let d = {};
  try { d = event.data ? event.data.json() : {}; } catch (e) { d = { title: 'ResolveHQ', body: event.data && event.data.text() }; }
  const title = d.title || 'ResolveHQ';
  const opts = {
    body: d.body || 'New activity from a customer',
    tag: d.tag || 'rhq',
    renotify: true,
    requireInteraction: !!d.urgent,          // urgent alerts stay until someone clicks
    icon: '/icons/icon-192.png',
    badge: '/icons/badge-96.png',
    data: { url: d.url || '/company-portal' },
    timestamp: Date.now(),
  };
  event.waitUntil(self.registration.showNotification(title, opts));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  const target = new URL(event.notification.data && event.notification.data.url || '/company-portal', self.location.origin).href;
  event.waitUntil((async () => {
    const all = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    for (const c of all) {
      if (c.url.includes('/company-portal')) {
        await c.focus();
        c.postMessage({ type: 'open-ticket', url: target });
        return;
      }
    }
    await self.clients.openWindow(target);
  })());
});
