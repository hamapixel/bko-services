import Link from "next/link";

export default function OfflinePage() {
  return (
    <main className="offline-page">
      <section className="offline-card" aria-labelledby="offline-title">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">B</span>
          <span>BKO Services</span>
        </div>
        <p className="eyebrow">Mode hors connexion</p>
        <h1 id="offline-title">Internet est momentanément indisponible.</h1>
        <p className="intro">
          Les pages privées et les actions sensibles ne sont jamais simulées
          hors ligne. Une demande conservée sur cet appareil reste un
          <strong> brouillon non envoyé</strong> jusqu’à confirmation du serveur.
        </p>
        <Link className="primary-button" href="/">
          Réessayer
        </Link>
        <p className="build-note">
          Dès que le réseau revient, ouvrez votre brouillon et envoyez-le
          explicitement.
        </p>
      </section>
    </main>
  );
}
