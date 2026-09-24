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
          BKO Services devient installable sur téléphone et ordinateur. Le mode
          hors connexion protège les actions sensibles : un brouillon conservé
          localement reste clairement <strong>non envoyé</strong> tant que le
          serveur ne l’a pas confirmé.
        </p>

        <div className="pwa-summary" aria-label="Fonctions PWA disponibles">
          <div>
            <strong>Installable</strong>
            <span>Application plein écran depuis le navigateur compatible.</span>
          </div>
          <div>
            <strong>Connexion instable</strong>
            <span>Page hors ligne sûre et état réseau visible.</span>
          </div>
          <div>
            <strong>Brouillons locaux</strong>
            <span>Aucune demande n’est déclarée envoyée sans réponse serveur.</span>
          </div>
        </div>

        <p className="build-note">Étape 19 · PWA et fonctionnement hors connexion</p>
      </div>
    </main>
  );
}
