self.addEventListener("push", (event) => {
  let payload = {
    title: "BKO Services",
    body: "Vous avez une nouvelle notification.",
    url: "/",
  };

  if (event.data) {
    try {
      payload = { ...payload, ...event.data.json() };
    } catch {
      payload.body = event.data.text();
    }
  }

  const options = {
    body: payload.body,
    tag: payload.notificationId ? `bko-${payload.notificationId}` : undefined,
    data: {
      url: payload.url || "/",
      notificationId: payload.notificationId || null,
      requestId: payload.requestId || null,
      kind: payload.kind || null,
    },
  };

  event.waitUntil(
    self.registration.showNotification(payload.title || "BKO Services", options),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  const targetUrl = new URL(
    event.notification.data?.url || "/",
    self.location.origin,
  ).href;

  event.waitUntil(
    self.clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((clients) => {
        for (const client of clients) {
          if (client.url === targetUrl && "focus" in client) {
            return client.focus();
          }
        }
        return self.clients.openWindow(targetUrl);
      }),
  );
});
