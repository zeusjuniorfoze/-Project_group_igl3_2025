import unittest
import re
from datetime import date, datetime, time, timedelta, timezone
from unittest.mock import patch

from app import create_app
from app.database import db
from app.models import (
    ActeNaissance,
    DossierNaissance,
    Hopital,
    Mairie,
    RoleUtilisateur,
    Utilisateur,
)
from app.routes.auth import _hash_reset_code
from app.services.acte_pdf import generer_pdf_acte, resolve_wkhtmltopdf_path


class AuthenticationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-session-signing-key",
                "JWT_SECRET_KEY": "test-jwt-signing-key",
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "SQLALCHEMY_TRACK_MODIFICATIONS": False,
                "WTF_CSRF_ENABLED": False,
                "MAIL_SUPPRESS_SEND": True,
                "MAIL_DEFAULT_SENDER": "test@example.org",
            }
        )

    def setUp(self):
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.drop_all()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def create_user(self, role, **kwargs):
        user = Utilisateur(
            nom_utilisateur=kwargs.pop("username", f"user-{role.name.lower()}"),
            email=kwargs.pop("email", f"{role.name.lower()}@example.org"),
            role=role,
            **kwargs,
        )
        user.set_password("KnownTestPassword123!")
        db.session.add(user)
        db.session.commit()
        return user

    def test_admin_routes_reject_anonymous_and_non_admin_users(self):
        response = self.client.get("/admin/admin")
        self.assertEqual(response.status_code, 302)

        hospital = Hopital(
            nom="Test Hospital",
            localisation="Yaounde",
            region="Centre",
        )
        db.session.add(hospital)
        db.session.commit()
        user = self.create_user(
            RoleUtilisateur.AGENT_HOPITAL,
            hopital_id=hospital.id,
        )

        with self.client.session_transaction() as client_session:
            client_session["utilisateur_id"] = user.id
        response = self.client.get("/admin/admin")
        self.assertEqual(response.status_code, 403)

    def test_admin_dashboard_renders_responsive_sidebar_toggle(self):
        admin = self.create_user(RoleUtilisateur.ADMIN)
        with self.client.session_transaction() as client_session:
            client_session["utilisateur_id"] = admin.id

        response = self.client.get("/admin/admin")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'id="adminSidebar"', response.data)
        self.assertIn(b'class="mobile-menu-btn"', response.data)
        self.assertIn(b'aria-controls="adminSidebar"', response.data)
        self.assertIn(b'class="sidebar-scrim"', response.data)

    def test_hospital_and_municipal_routes_enforce_roles(self):
        mairie = Mairie(
            nom="Test Mairie",
            localisation="Yaounde",
            region="Centre",
        )
        db.session.add(mairie)
        db.session.commit()
        hospital_agent = self.create_user(
            RoleUtilisateur.AGENT_HOPITAL,
            hopital_id=1,
        )

        with self.client.session_transaction() as client_session:
            client_session["utilisateur_id"] = hospital_agent.id
        self.assertEqual(self.client.get("/mairie/dashboard").status_code, 403)

        municipal_agent = self.create_user(
            RoleUtilisateur.AGENT_MAIRIE,
            username="municipal-agent",
            email="municipal@example.org",
            mairie_id=mairie.id,
        )
        with self.client.session_transaction() as client_session:
            client_session.clear()
            client_session["utilisateur_id"] = municipal_agent.id
        self.assertEqual(self.client.get("/mairie/dashboard").status_code, 200)

    def test_hospital_and_mairie_declarations_keep_correct_origin(self):
        hospital = Hopital(
            nom="Declaration Hospital",
            localisation="Yaounde",
            region="Centre",
        )
        mairie = Mairie(
            nom="Declaration Mairie",
            localisation="Yaounde",
            region="Centre",
        )
        db.session.add_all([hospital, mairie])
        db.session.commit()

        hospital_agent = self.create_user(
            RoleUtilisateur.AGENT_HOPITAL,
            username="declaration-hospital-agent",
            email="declaration-hospital@example.org",
            hopital_id=hospital.id,
        )
        mairie_agent = self.create_user(
            RoleUtilisateur.AGENT_MAIRIE,
            username="declaration-mairie-agent",
            email="declaration-mairie@example.org",
            mairie_id=mairie.id,
        )
        declaration_data = {
            "nom_enfant": "Test",
            "prenom_enfant": "Child",
            "sexe_enfant": "Masculin",
            "date_naissance": "2025-01-01",
            "heure_naissance": "12:00",
            "lieu_naissance": "Yaounde",
            "nom_mere": "Parent",
            "prenom_mere": "Test",
        }

        with self.client.session_transaction() as client_session:
            client_session["utilisateur_id"] = hospital_agent.id
        response = self.client.post(
            "/hopital/ajouter_declaration",
            data=declaration_data,
        )
        self.assertEqual(response.status_code, 302)

        with self.client.session_transaction() as client_session:
            client_session.clear()
            client_session["utilisateur_id"] = mairie_agent.id
        response = self.client.post(
            "/mairie/ajouter_declaration",
            data=declaration_data,
        )
        self.assertEqual(response.status_code, 302)

        declarations = DossierNaissance.query.order_by(DossierNaissance.id).all()
        self.assertEqual(len(declarations), 2)
        self.assertEqual(declarations[0].hopital_id, hospital.id)
        self.assertEqual(declarations[0].soumis_par_utilisateur_id, hospital_agent.id)
        self.assertIsNone(declarations[0].mairie_id)
        self.assertIsNone(declarations[1].hopital_id)
        self.assertEqual(declarations[1].mairie_id, mairie.id)
        self.assertEqual(declarations[1].soumis_par_utilisateur_id, mairie_agent.id)

    def test_birth_certificate_template_receives_dossier_and_acte(self):
        mairie = Mairie(
            nom="Mairie PDF",
            localisation="Yaounde",
            region="Centre",
        )
        db.session.add(mairie)
        db.session.commit()
        utilisateur = self.create_user(
            RoleUtilisateur.ADMIN,
            username="pdf-admin",
            email="pdf-admin@example.org",
        )
        dossier = DossierNaissance(
            nom_enfant="TEST",
            prenom_enfant="CHILD",
            sexe_enfant="Masculin",
            date_naissance=date(2025, 1, 2),
            heure_naissance=time(10, 30),
            lieu_naissance="Yaounde",
            nom_mere="PARENT",
            prenom_mere="TEST",
            mairie_id=mairie.id,
            hopital_id=None,
            soumis_par_utilisateur_id=utilisateur.id,
        )
        db.session.add(dossier)
        db.session.flush()
        acte = ActeNaissance(
            numero_acte="2025/PDF/1",
            date_enregistrement=datetime(2025, 1, 3),
            lieu_enregistrement="Yaounde",
            nom_complet_enfant="TEST CHILD",
            sexe_enfant="Masculin",
            date_naissance_enfant=date(2025, 1, 2),
            heure_naissance_enfant=time(10, 30),
            lieu_naissance_enfant="Yaounde",
            nom_complet_mere="PARENT TEST",
            dossier_naissance_id=dossier.id,
            mairie_id=mairie.id,
            genere_par_utilisateur_id=utilisateur.id,
        )
        db.session.add(acte)
        db.session.commit()

        with (
            patch("app.services.acte_pdf.pdfkit.from_string") as pdf_renderer,
            patch("app.services.acte_pdf._pdfkit_config", return_value=None),
        ):
            chemin_pdf = generer_pdf_acte(dossier, acte)

        html_genere = pdf_renderer.call_args.args[0]
        self.assertIn("2025/PDF/1", html_genere)
        self.assertIn("TEST Child", html_genere)
        self.assertIn("Mairie PDF", html_genere)
        self.assertTrue(chemin_pdf.startswith("pdfs/acte_"))

    def test_wkhtmltopdf_path_uses_configured_executable(self):
        configured_path = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
        with (
            patch.dict(self.app.config, {"WKHTMLTOPDF_PATH": configured_path}),
            patch("app.services.acte_pdf.os.path.isfile", return_value=True),
        ):
            self.assertEqual(resolve_wkhtmltopdf_path(), configured_path)

    def test_missing_wkhtmltopdf_has_actionable_error(self):
        with (
            patch.dict(self.app.config, {"WKHTMLTOPDF_PATH": None}),
            patch("app.services.acte_pdf.shutil.which", return_value=None),
            patch("app.services.acte_pdf.os.path.isfile", return_value=False),
        ):
            with self.assertRaisesRegex(FileNotFoundError, "WKHTMLTOPDF_PATH"):
                resolve_wkhtmltopdf_path()

    def test_agency_agents_cannot_modify_other_agency_records(self):
        hospital_a = Hopital(
            nom="Hospital A",
            localisation="Yaounde",
            region="Centre",
        )
        hospital_b = Hopital(
            nom="Hospital B",
            localisation="Douala",
            region="Littoral",
        )
        mairie_a = Mairie(
            nom="Mairie A",
            localisation="Yaounde",
            region="Centre",
        )
        mairie_b = Mairie(
            nom="Mairie B",
            localisation="Douala",
            region="Littoral",
        )
        db.session.add_all([hospital_a, hospital_b, mairie_a, mairie_b])
        db.session.commit()
        hospital_agent = self.create_user(
            RoleUtilisateur.AGENT_HOPITAL,
            username="hospital-agent",
            email="hospital-agent@example.org",
            hopital_id=hospital_a.id,
        )
        mairie_agent = self.create_user(
            RoleUtilisateur.AGENT_MAIRIE,
            username="mairie-agent",
            email="mairie-agent@example.org",
            mairie_id=mairie_a.id,
        )
        dossier = DossierNaissance(
            nom_enfant="Test",
            prenom_enfant="Child",
            sexe_enfant="Inconnu",
            date_naissance=date(2025, 1, 1),
            heure_naissance=time(12, 0),
            lieu_naissance="Douala",
            nom_mere="Parent",
            prenom_mere="Test",
            hopital_id=hospital_b.id,
            mairie_id=mairie_b.id,
            soumis_par_utilisateur_id=hospital_agent.id,
        )
        db.session.add(dossier)
        db.session.commit()

        with self.client.session_transaction() as client_session:
            client_session["utilisateur_id"] = hospital_agent.id
            client_session["role"] = RoleUtilisateur.ADMIN.value
            client_session["hopital_id"] = hospital_b.id
        response = self.client.post(
            f"/hopital/modifier_declaration/{dossier.id}",
            data={},
        )
        self.assertEqual(response.status_code, 404)

        with self.client.session_transaction() as client_session:
            client_session.clear()
            client_session["utilisateur_id"] = mairie_agent.id
            client_session["mairie_id"] = mairie_b.id
        response = self.client.post(
            f"/mairie/declaration/{dossier.id}/valider",
            data={"statut": "Validé"},
        )
        self.assertEqual(response.status_code, 404)

    def test_successful_login_clears_pre_authentication_session(self):
        admin = self.create_user(RoleUtilisateur.ADMIN)
        with self.client.session_transaction() as client_session:
            client_session["email_verified"] = admin.email
            client_session["untrusted"] = "stale"

        response = self.client.post(
            "/auth/login",
            data={"email": admin.email, "mot_de_passe": "KnownTestPassword123!"},
        )
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as client_session:
            self.assertEqual(client_session["utilisateur_id"], admin.id)
            self.assertNotIn("email_verified", client_session)
            self.assertNotIn("untrusted", client_session)

    def test_admin_password_update_uses_the_login_password_hasher(self):
        admin = self.create_user(RoleUtilisateur.ADMIN)
        with self.client.session_transaction() as client_session:
            client_session["utilisateur_id"] = admin.id
        response = self.client.post(
            f"/admin/utilisateur/modifier/{admin.id}",
            data={
                "nom_utilisateur": admin.nom_utilisateur,
                "email": admin.email,
                "role": RoleUtilisateur.ADMIN.name,
                "mot_de_passe": "ChangedPassword123!",
            },
        )
        self.assertEqual(response.status_code, 302)
        db.session.expire_all()
        admin = db.session.get(Utilisateur, admin.id)
        self.assertTrue(admin.check_password("ChangedPassword123!"))

    def test_password_reset_code_is_hashed_and_attempt_limit_is_persistent(self):
        user = self.create_user(RoleUtilisateur.ADMIN)
        user.reset_code = _hash_reset_code("123456")
        user.reset_code_expiry = datetime.now(timezone.utc) + timedelta(minutes=20)
        db.session.commit()
        self.assertNotEqual(user.reset_code, "123456")
        with self.client.session_transaction() as client_session:
            client_session["email_reset"] = user.email

        for _ in range(5):
            self.client.post(
                "/auth/verify-code",
                data={"code": "000000"},
            )
            db.session.expire_all()
            user = db.session.get(Utilisateur, user.id)

        self.assertIsNone(user.reset_code)
        self.assertEqual(user.reset_attempts, 0)
        with self.client.session_transaction() as client_session:
            self.assertNotIn("email_reset", client_session)

    def test_password_reset_requires_verified_code_and_updates_password(self):
        user = self.create_user(RoleUtilisateur.ADMIN)
        user.reset_code = _hash_reset_code("123456")
        user.reset_code_expiry = datetime.now(timezone.utc) + timedelta(minutes=20)
        db.session.commit()
        with self.client.session_transaction() as client_session:
            client_session["email_reset"] = user.email

        self.client.post("/auth/verify-code", data={"code": "123456"})
        response = self.client.post(
            "/auth/reset-password",
            data={
                "password": "ReplacementPassword123!",
                "confirm_password": "ReplacementPassword123!",
            },
        )
        self.assertEqual(response.status_code, 302)
        db.session.expire_all()
        user = db.session.get(Utilisateur, user.id)
        self.assertTrue(user.check_password("ReplacementPassword123!"))
        self.assertFalse(user.reset_verified)

    def test_unknown_email_stays_on_form_without_generating_or_sending_code(self):
        user = self.create_user(RoleUtilisateur.ADMIN)
        with patch("app.routes.auth.mail.send") as send_mail:
            response = self.client.post(
                "/auth/forgetpassword",
                data={"email": "unknown@example.org"},
            )

        self.assertEqual(response.status_code, 200)
        response_html = response.get_data(as_text=True)
        self.assertIn("Aucun compte", response_html)
        self.assertIn("cette adresse e-mail", response_html)
        send_mail.assert_not_called()
        db.session.refresh(user)
        self.assertIsNone(user.reset_code)
        self.assertIsNone(user.reset_code_expiry)
        self.assertIsNone(user.reset_requested_at)
        with self.client.session_transaction() as client_session:
            self.assertNotIn("email_reset", client_session)

    def test_existing_email_sends_code_and_redirects_to_verification(self):
        user = self.create_user(RoleUtilisateur.ADMIN)
        with patch("app.routes.auth.mail.send") as send_mail:
            response = self.client.post(
                "/auth/forgetpassword",
                data={"email": user.email},
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/auth/verify-code")
        send_mail.assert_called_once()
        db.session.refresh(user)
        self.assertTrue(user.reset_code)
        self.assertIsNotNone(user.reset_code_expiry)

    def test_verification_page_requires_a_successful_reset_request(self):
        response = self.client.get("/auth/verify-code")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/auth/forgetpassword")

    def test_mail_failure_invalidates_reset_code_and_allows_retry(self):
        user = self.create_user(RoleUtilisateur.ADMIN)
        with patch(
            "app.routes.auth.mail.send",
            side_effect=RuntimeError("simulated SMTP failure"),
        ):
            response = self.client.post(
                "/auth/forgetpassword",
                data={"email": user.email},
            )

        self.assertEqual(response.status_code, 302)
        db.session.expire_all()
        user = db.session.get(Utilisateur, user.id)
        self.assertIsNone(user.reset_code)
        self.assertIsNone(user.reset_code_expiry)
        self.assertIsNone(user.reset_requested_at)
        self.assertFalse(user.reset_verified)
        with self.client.session_transaction() as client_session:
            self.assertNotIn("email_reset", client_session)

    def test_successful_mail_submission_sets_reset_session(self):
        user = self.create_user(RoleUtilisateur.ADMIN)
        with patch("app.routes.auth.mail.send") as send_mail:
            response = self.client.post(
                "/auth/forgetpassword",
                data={"email": user.email},
            )

        self.assertEqual(response.status_code, 302)
        send_mail.assert_called_once()
        with self.client.session_transaction() as client_session:
            self.assertEqual(client_session["email_reset"], user.email)

    def test_reset_cooldown_without_active_code_stays_on_request_form(self):
        user = self.create_user(RoleUtilisateur.ADMIN)
        user.reset_requested_at = datetime.now(timezone.utc)
        db.session.commit()

        with patch("app.routes.auth.mail.send") as send_mail:
            response = self.client.post(
                "/auth/forgetpassword",
                data={"email": user.email},
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/auth/forgetpassword")
        send_mail.assert_not_called()

    def test_login_post_requires_csrf_token_when_csrf_is_enabled(self):
        self.app.config["WTF_CSRF_ENABLED"] = True
        try:
            response = self.client.post(
                "/auth/login",
                data={"email": "nobody@example.org", "mot_de_passe": "wrong"},
            )
            self.assertEqual(response.status_code, 400)

            login_page = self.client.get("/auth/login")
            token_match = re.search(
                r'name="csrf_token" value="([^"]+)"',
                login_page.get_data(as_text=True),
            )
            self.assertIsNotNone(token_match)
            valid_token_response = self.client.post(
                "/auth/login",
                data={
                    "csrf_token": token_match.group(1),
                    "email": "nobody@example.org",
                    "mot_de_passe": "wrong",
                },
            )
            self.assertEqual(valid_token_response.status_code, 302)
            self.assertEqual(self.client.get("/auth/logout").status_code, 405)
        finally:
            self.app.config["WTF_CSRF_ENABLED"] = False


if __name__ == "__main__":
    unittest.main()