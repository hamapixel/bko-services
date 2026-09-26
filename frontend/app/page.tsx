import Link from "next/link";

export default function Home() {
  return (
    <main className="home-premium">
      <section className="home-premium-shell">
        <header className="home-premium-topbar">
          <div className="home-premium-brand" aria-label="BKO Services">
            <span className="home-premium-mark" aria-hidden="true">B</span>
            <span>
              <strong>BKO Services</strong>
              <small>Bamako</small>
            </span>
          </div>

          <div className="home-premium-nav">
            <Link className="home-premium-login" href="/connexion">
              Connexion client
            </Link>
            <Link className="home-premium-provider-login" href="/prestataire/connexion">
              Connexion prestataire
            </Link>
            <Link className="home-premium-become" href="/prestataire/devenir">
              Créer compte prestataire
            </Link>
          </div>
        </header>

        <div className="home-premium-grid">
          <div className="home-premium-copy">
            <span className="home-premium-badge">Services de proximité à Bamako</span>
            <h1>
              Trouvez le bon professionnel.
              <span> Rapidement.</span>
            </h1>
            <p>
              Décrivez votre besoin, recevez un prestataire vérifié et suivez
              chaque étape de l’intervention depuis votre téléphone.
            </p>

            <div className="home-premium-actions">
              <Link className="home-premium-primary" href="/connexion">
                Trouver un professionnel
              </Link>
              <Link className="home-premium-secondary" href="/connexion">
                Créer mon compte
              </Link>
            </div>

            <div className="home-premium-trust">
              <span><strong>✓</strong> Prestataires vérifiés</span>
              <span><strong>✓</strong> Suivi clair</span>
              <span><strong>✓</strong> Coordonnées protégées</span>
            </div>
            <a className="home-discover-link" href="#fonctionnement">Découvrir comment ça marche <span aria-hidden="true">↓</span></a>
          </div>

          <div className="home-premium-showcase" aria-hidden="true">
            <div className="home-phone-card">
              <div className="home-phone-head">
                <span className="home-phone-mini-mark">B</span>
                <div>
                  <strong>BKO Services</strong>
                  <small>Votre demande</small>
                </div>
                <span className="home-online-dot" />
              </div>

              <div className="home-phone-welcome">
                <small>Bonjour 👋</small>
                <strong>De quoi avez-vous besoin ?</strong>
              </div>

              <div className="home-service-grid">
                <div><span>⚡</span><strong>Électricité</strong></div>
                <div><span>🔧</span><strong>Plomberie</strong></div>
                <div><span>❄</span><strong>Climatisation</strong></div>
                <div><span>＋</span><strong>Voir plus</strong></div>
              </div>

              <div className="home-status-card">
                <div className="home-status-top">
                  <span>Intervention en cours</span>
                  <strong>En route</strong>
                </div>
                <div className="home-status-line"><span /></div>
                <div className="home-provider-mini">
                  <span>✓</span>
                  <div>
                    <strong>Prestataire attribué</strong>
                    <small>Profil vérifié</small>
                  </div>
                </div>
              </div>
              <span className="home-preview-label">Aperçu illustratif</span>
            </div>

            <div className="home-float-card home-float-verified">
              <span>✓</span>
              <div>
                <strong>Prestataire vérifié</strong>
                <small>Identité contrôlée</small>
              </div>
            </div>

            <div className="home-float-card home-float-fast">
              <span>↗</span>
              <div>
                <strong>Suivi simple</strong>
                <small>Chaque étape visible</small>
              </div>
            </div>
          </div>
        </div>

        <div className="home-premium-bottom">
          <article>
            <span>01</span>
            <div>
              <strong>Décrivez votre besoin</strong>
              <small>Quelques informations suffisent.</small>
            </div>
          </article>
          <article>
            <span>02</span>
            <div>
              <strong>Un professionnel est proposé</strong>
              <small>Selon son métier et sa zone.</small>
            </div>
          </article>
          <article>
            <span>03</span>
            <div>
              <strong>Suivez l’intervention</strong>
              <small>Jusqu’à votre confirmation finale.</small>
            </div>
          </article>
        </div>

        <section className="home-story-section" id="fonctionnement" aria-labelledby="home-story-title">
          <div className="home-section-heading">
            <span className="home-section-kicker">SIMPLE À CHAQUE ÉTAPE</span>
            <h2 id="home-story-title">Du besoin à l’intervention, tout reste clair.</h2>
            <p>Une demande précise aide à trouver un professionnel qui exerce le bon métier et dessert votre quartier.</p>
          </div>
          <div className="home-story-grid">
            <article className="home-story-card">
              <span className="home-story-symbol" aria-hidden="true">01</span>
              <h3>Décrivez le problème</h3>
              <p>Choisissez le métier, le quartier et la priorité. Vous pouvez suivre votre demande depuis votre espace.</p>
            </article>
            <article className="home-story-card">
              <span className="home-story-symbol" aria-hidden="true">02</span>
              <h3>Recevez une proposition</h3>
              <p>Les prestataires éligibles de votre zone peuvent recevoir l’offre. Vos coordonnées restent privées avant l’attribution.</p>
            </article>
            <article className="home-story-card">
              <span className="home-story-symbol" aria-hidden="true">03</span>
              <h3>Suivez et donnez votre avis</h3>
              <p>Consultez l’avancement de l’intervention, confirmez la fin du travail et évaluez le prestataire.</p>
            </article>
          </div>
        </section>

        <section className="home-provider-section" aria-labelledby="home-provider-title">
          <div>
            <span className="home-section-kicker">VOUS ÊTES PROFESSIONNEL ?</span>
            <h2 id="home-provider-title">Vos compétences, près des clients de votre quartier.</h2>
            <p>Créez votre profil, indiquez vos métiers et les quartiers desservis. Après vérification, un abonnement actif vous permet de recevoir les offres qui vous correspondent.</p>
            <div className="home-provider-actions">
              <Link className="home-premium-primary" href="/prestataire/devenir">Créer mon compte prestataire</Link>
              <Link className="home-provider-text-link" href="/prestataire/connexion">Déjà inscrit ? Se connecter <span aria-hidden="true">↗</span></Link>
            </div>
          </div>
          <div className="home-provider-visual" aria-hidden="true">
            <div className="home-provider-visual-top"><span>✓</span> Espace prestataire</div>
            <div className="home-provider-visual-main">
              <small>VOTRE ACTIVITÉ</small>
              <strong>Des offres adaptées à votre métier.</strong>
              <span>Métiers · Quartiers · Disponibilité</span>
            </div>
            <div className="home-provider-visual-foot"><span /> Un espace pour suivre vos interventions</div>
          </div>
        </section>

        <footer className="home-premium-footer">
          <span>BKO Services · Bamako</span>
          <Link href="/connexion">Accéder à mon espace client <span aria-hidden="true">↗</span></Link>
        </footer>
      </section>
    </main>
  );
}
