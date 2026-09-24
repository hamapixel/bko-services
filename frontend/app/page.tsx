import Link from "next/link";

export default function Home() {
  return (
    <main className="home">
      <div className="home-card">
        <div className="brand" aria-label="BKO Services">
          <span className="brand-mark" aria-hidden="true">B</span>
          <span>BKO Services</span>
        </div>
        <p className="eyebrow">Bamako · Services de proximité</p>
        <h1>Le bon professionnel, au bon moment.</h1>
        <p className="intro">
          Décrivez votre besoin, suivez l’intervention et gardez le contrôle
          depuis votre téléphone. Les brouillons restent clairement
          <strong> non envoyés</strong> tant que le serveur ne les a pas reçus.
        </p>

        <div className="home-actions">
          <Link className="button-primary" href="/connexion">
            Accéder à l’espace client
          </Link>
          <Link className="button-secondary" href="/connexion">
            Créer un compte
          </Link>
        </div>

        <div className="pwa-summary" aria-label="Fonctions disponibles">
          <div>
            <strong>Professionnels vérifiés</strong>
            <span>Suivi du prestataire attribué et de chaque étape.</span>
          </div>
          <div>
            <strong>Connexion instable</strong>
            <span>Brouillons locaux et état hors connexion explicite.</span>
          </div>
          <div>
            <strong>Suivi complet</strong>
            <span>Confirmation de fin et avis après l’intervention.</span>
          </div>
        </div>

        <p className="build-note">BKO Services · Espace client responsive</p>
      </div>
    </main>
  );
}
