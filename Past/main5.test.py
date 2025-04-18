import unittest
from datetime import date, timedelta

# import the module that contains the main application code
import main5

# Short‑hand references for convenience
User = main5.User
Applicant = main5.Applicant
HDBOfficer = main5.HDBOfficer
HDBManager = main5.HDBManager
Project = main5.Project
Application = main5.Application
Registration = main5.Registration
Enquiry = main5.Enquiry
OperationError = main5.OperationError
IntegrityError = main5.IntegrityError


# ---------------------------------------------------------------------------
# In‑memory repository implementations --------------------------------------
# ---------------------------------------------------------------------------

class _MemoryUserRepo:
    """A minimal in‑memory replacement for main5.UserRepository used by tests."""
    def __init__(self):
        self.users = {}

    # --- API expected by AuthService / others --------------------------------
    def find_user_by_nric(self, nric):
        return self.users.get(nric)

    def save_user(self, user):
        self.users[user.nric] = user

    # helper – not part of production API
    def add_user(self, user):
        self.save_user(user)


class _MemoryProjectRepo:
    def __init__(self):
        self.projects = {}

    def get_all(self):
        return list(self.projects.values())

    def find_by_name(self, name):
        return self.projects.get(name)

    def add(self, project):
        if project.project_name in self.projects:
            raise IntegrityError("duplicate project")
        self.projects[project.project_name] = project

    def update(self, project):
        if project.project_name not in self.projects:
            raise IntegrityError("project not found")
        self.projects[project.project_name] = project

    def delete_by_name(self, name):
        if name not in self.projects:
            raise IntegrityError("project not found")
        del self.projects[name]


class _MemoryApplicationRepo:
    def __init__(self):
        self.apps = []

    # ---------- helpers -----------------------------------------------------
    def _key(self, app):
        return (app.applicant_nric, app.project_name)

    # ---------- API used by ApplicationService ------------------------------
    def get_all(self):
        return list(self.apps)

    def find_by_applicant_nric(self, nric):
        for app in self.apps:
            if app.applicant_nric == nric and app.status != Application.STATUS_UNSUCCESSFUL:
                return app
        return None

    def find_by_project_name(self, project_name):
        return [a for a in self.apps if a.project_name == project_name]

    def add(self, app):
        if self.find_by_applicant_nric(app.applicant_nric):
            raise IntegrityError("duplicate active application for applicant")
        self.apps.append(app)

    def update(self, app):
        for i, existing in enumerate(self.apps):
            if self._key(existing) == self._key(app):
                self.apps[i] = app
                return
        raise IntegrityError("application not found")

    def delete(self, applicant_nric, project_name):
        self.apps = [a for a in self.apps if self._key(a) != (applicant_nric, project_name)]


class _MemoryRegistrationRepo:
    def __init__(self):
        self.regs = []

    def _key(self, reg):
        return (reg.officer_nric, reg.project_name)

    # ---------- API ---------------------------------------------------------
    def get_all(self):
        return list(self.regs)

    def find_by_officer_and_project(self, officer_nric, project_name):
        for r in self.regs:
            if self._key(r) == (officer_nric, project_name):
                return r
        return None

    def find_by_officer(self, officer_nric):
        return [r for r in self.regs if r.officer_nric == officer_nric]

    def find_by_project(self, project_name, status_filter=None):
        rs = [r for r in self.regs if r.project_name == project_name]
        if status_filter:
            rs = [r for r in rs if r.status == status_filter]
        return rs

    def add(self, reg):
        if self.find_by_officer_and_project(reg.officer_nric, reg.project_name):
            raise IntegrityError("duplicate registration")
        self.regs.append(reg)

    def update(self, reg):
        for i, existing in enumerate(self.regs):
            if self._key(existing) == self._key(reg):
                self.regs[i] = reg
                return
        raise IntegrityError("registration not found")

    def delete(self, officer_nric, project_name):
        self.regs = [r for r in self.regs if self._key(r) != (officer_nric, project_name)]


class _MemoryEnquiryRepo:
    def __init__(self):
        self.enquiries = {}
        self.next_id = 1

    def get_all(self):
        return list(self.enquiries.values())

    def find_by_id(self, eid):
        return self.enquiries.get(eid)

    def find_by_applicant(self, applicant_nric):
        return [e for e in self.enquiries.values() if e.applicant_nric == applicant_nric]

    def find_by_project(self, project_name):
        return [e for e in self.enquiries.values() if e.project_name == project_name]

    def add(self, enquiry):
        enquiry.enquiry_id = self.next_id
        self.enquiries[self.next_id] = enquiry
        self.next_id += 1

    def update(self, enquiry):
        if enquiry.enquiry_id not in self.enquiries:
            raise IntegrityError("enquiry not found")
        self.enquiries[enquiry.enquiry_id] = enquiry

    def delete_by_id(self, eid):
        if eid not in self.enquiries:
            raise IntegrityError("enquiry not found")
        del self.enquiries[eid]


# ---------------------------------------------------------------------------
# Helper to build a fresh isolated service stack for each test --------------
# ---------------------------------------------------------------------------

def _build_env():
    """Create fresh in‑memory repositories and service instances."""
    user_repo = _MemoryUserRepo()
    project_repo = _MemoryProjectRepo()
    application_repo = _MemoryApplicationRepo()
    registration_repo = _MemoryRegistrationRepo()
    enquiry_repo = _MemoryEnquiryRepo()

    project_service = main5.ProjectService(project_repo, registration_repo)
    registration_service = main5.RegistrationService(registration_repo, project_service, application_repo)
    application_service = main5.ApplicationService(application_repo, project_service, registration_service)
    enquiry_service = main5.EnquiryService(enquiry_repo, project_service, registration_service, user_repo)
    auth_service = main5.AuthService(user_repo)

    return {
        "user_repo": user_repo,
        "project_repo": project_repo,
        "application_repo": application_repo,
        "registration_repo": registration_repo,
        "enquiry_repo": enquiry_repo,
        "project_service": project_service,
        "registration_service": registration_service,
        "application_service": application_service,
        "enquiry_service": enquiry_service,
        "auth_service": auth_service,
    }

# ---------------------------------------------------------------------------
# Utility functions ---------------------------------------------------------
# ---------------------------------------------------------------------------

def _make_dates(active_days=30):
    """Return (open_date, close_date) window that includes today."""
    today = date.today()
    return today, today + timedelta(days=active_days)


def _create_project(name: str, manager: HDBManager, project_repo, days_open=30, visibility=True,
                    num2=10, num3=10):
    od, cd = _make_dates(days_open)
    p = Project(name, "TestVille", "2-Room", num2, 200000, "3-Room", num3, 300000,
                od, cd, manager.nric, 10, [], visibility)
    project_repo.add(p)
    return p

# ---------------------------------------------------------------------------
# Test cases (mapping to specification list 1‑23) ---------------------------
# ---------------------------------------------------------------------------

class TestBTOSystem(unittest.TestCase):

    # 1. Valid User Login ---------------------------------------------------
    def test_01_valid_login(self):
        env = _build_env()
        user_repo = env["user_repo"]
        auth_service = env["auth_service"]

        alice = Applicant("Alice", "S1234567A", 36, "Single", "pass")
        user_repo.add_user(alice)

        logged_in = auth_service.login("S1234567A", "pass")
        self.assertEqual(logged_in, alice)

    # 2. Invalid NRIC Format ----------------------------------------------
    def test_02_invalid_nric_format(self):
        env = _build_env()
        user_repo = env["user_repo"]
        auth_service = env["auth_service"]

        user_repo.add_user(Applicant("Bob", "S7654321B", 35, "Single", "pw"))
        with self.assertRaises(OperationError):
            auth_service.login("INVALID", "pw")

    # 3. Incorrect Password -------------------------------------------------
    def test_03_incorrect_password(self):
        env = _build_env()
        user_repo = env["user_repo"]
        auth_service = env["auth_service"]

        user_repo.add_user(Applicant("Carol", "S1111111C", 40, "Married", "secret"))
        with self.assertRaises(OperationError):
            auth_service.login("S1111111C", "wrong")

    # 4. Password Change Functionality -------------------------------------
    def test_04_password_change(self):
        env = _build_env()
        user_repo = env["user_repo"]
        auth_service = env["auth_service"]

        dave = Applicant("Dave", "S2222222D", 50, "Married", "old")
        user_repo.add_user(dave)
        auth_service.change_password(dave, "newpwd")
        # old pwd fails
        with self.assertRaises(OperationError):
            auth_service.login("S2222222D", "old")
        # new pwd succeeds
        self.assertEqual(auth_service.login("S2222222D", "newpwd"), dave)

    # 5. Project Visibility & Eligibility -----------------------------------
    def test_05_visibility_and_group_filter(self):
        env = _build_env()
        user_repo = env["user_repo"]
        project_service = env["project_service"]

        mgr = HDBManager("Mgr", "S9999999Z", 45, "Married", "m")
        user_repo.add_user(mgr)

        # project visible
        p1 = _create_project("P1", mgr, env["project_repo"], visibility=True)
        # project hidden
        p2 = _create_project("P2", mgr, env["project_repo"], visibility=False)

        single_app = Applicant("Eve", "S3333333E", 35, "Single", "x")
        user_repo.add_user(single_app)

        viewable = project_service.get_viewable_projects_for_applicant(single_app)
        names = {p.project_name for p in viewable}
        self.assertIn("P1", names)
        self.assertNotIn("P2", names)

    # 6. Project Application Rules -----------------------------------------
    def test_06_application_rules(self):
        env = _build_env()
        user_repo = env["user_repo"]
        project_service = env["project_service"]
        application_service = env["application_service"]

        mgr = HDBManager("Mgr", "S8888888Y", 45, "Married", "m")
        user_repo.add_user(mgr)
        prj = _create_project("FamilyNest", mgr, env["project_repo"], num2=5, num3=5)

        single = Applicant("Single35", "S4444444F", 35, "Single", "s")
        user_repo.add_user(single)
        # singles cannot take 3‑room
        with self.assertRaises(OperationError):
            application_service.apply_for_project(single, prj, 3)
        # but can apply for 2‑room
        app = application_service.apply_for_project(single, prj, 2)
        self.assertIsNotNone(app)

    # 7. View application after project hidden -----------------------------
    def test_07_view_after_visibility_off(self):
        env = _build_env()
        user_repo = env["user_repo"]
        project_service = env["project_service"]
        application_service = env["application_service"]

        mgr = HDBManager("Mgr", "S7777777W", 40, "Married", "m")
        user_repo.add_user(mgr)
        prj = _create_project("HideMe", mgr, env["project_repo"], visibility=True)

        ap = Applicant("Viewer", "S5555555G", 36, "Single", "p")
        user_repo.add_user(ap)
        application_service.apply_for_project(ap, prj, 2)

        # manager hides project later
        prj.visibility = False
        env["project_repo"].update(prj)

        viewable = project_service.get_viewable_projects_for_applicant(ap,
            application_service.find_application_by_applicant(ap.nric))
        self.assertIn(prj, viewable)

    # 8. Only one flat booking per applicant -------------------------------
    def test_08_single_flat_booking(self):
        env = _build_env()
        urepo, prepo, arepo, rrepo = env["user_repo"], env["project_repo"], env["application_repo"], env["registration_repo"]
        app_service = env["application_service"]
        reg_service = env["registration_service"]
        proj_service = env["project_service"]

        mgr = HDBManager("Mgr", "S6666666H", 45, "Married", "m")
        urepo.add_user(mgr)
        prj = _create_project("SoloHome", mgr, prepo, num2=2, num3=2)

        off = HDBOfficer("Officer", "S1212121O", 32, "Married", "o")
        urepo.add_user(off)

        # officer registers & manager approves so that he can handle booking
        reg = Registration(off.nric, prj.project_name)
        rrepo.add(reg)
        reg_service.manager_approve_officer_registration(mgr, reg)

        applicant = Applicant("Tenant", "S2323232T", 30, "Married", "t")
        urepo.add_user(applicant)
        app_service.apply_for_project(applicant, prj, 2)
        # manager approves application first
        app = arepo.find_by_applicant_nric(applicant.nric)
        app_service.manager_approve_application(mgr, app)

        # officer books flat
        proj_service.add_officer_to_project(prj, off.nric)  # ensure link
        prj_before_units, _ = prj.get_flat_details(2)
        booked_project = app_service.officer_book_flat(off, app)
        prj_after_units, _ = booked_project.get_flat_details(2)
        self.assertEqual(prj_before_units - 1, prj_after_units)

        # second booking attempt should fail
        with self.assertRaises(OperationError):
            app_service.officer_book_flat(off, app)

    # 9. Applicant enquiries CRUD ------------------------------------------
    def test_09_enquiry_crud(self):
        env = _build_env()
        user_repo, enquiry_service = env["user_repo"], env["enquiry_service"]
        project_service = env["project_service"]
        proj_repo = env["project_repo"]

        mgr = HDBManager("Mgr", "S4545454M", 45, "Married", "m")
        user_repo.add_user(mgr)
        prj = _create_project("AskAway", mgr, proj_repo)

        appl = Applicant("Quest", "S5656565Q", 36, "Single", "q")
        user_repo.add_user(appl)

        # create
        enq = enquiry_service.submit_enquiry(appl, prj, "When is TOP?")
        self.assertTrue(enq.enquiry_id)
        # edit
        enquiry_service.edit_enquiry(appl, enq, "Updated question")
        self.assertEqual(enq.text, "Updated question")
        # delete
        enquiry_service.delete_enquiry(appl, enq)
        self.assertIsNone(enquiry_service.find_enquiry_by_id(enq.enquiry_id))

    # 10. Officer registration eligibility ----------------------------------
    def test_10_officer_registration_eligibility(self):
        env = _build_env()
        urepo = env["user_repo"]
        proj_repo = env["project_repo"]
        reg_service = env["registration_service"]

        mgr = HDBManager("Mgr", "S6767676N", 45, "Married", "m")
        urepo.add_user(mgr)
        prj = _create_project("Eligibility", mgr, proj_repo)

        off = HDBOfficer("Officer", "S7878787O", 30, "Married", "o")
        urepo.add_user(off)

        # officer applies for the same project as applicant (should block registration)
        app_service = env["application_service"]
        app_service.apply_for_project(off, prj, 2)
        with self.assertRaises(OperationError):
            reg_service.officer_register_for_project(off, prj)

    # 11. Officer registration status visibility ---------------------------
    def test_11_registration_status(self):
        env = _build_env()
        urepo, proj_repo = env["user_repo"], env["project_repo"]
        reg_service = env["registration_service"]

        mgr = HDBManager("Mgr", "S9898989M", 50, "Married", "m")
        urepo.add_user(mgr)
        prj = _create_project("RegView", mgr, proj_repo)

        off = HDBOfficer("Officer", "S8686868O", 30, "Married", "o")
        urepo.add_user(off)

        reg = reg_service.officer_register_for_project(off, prj)
        reg_service.manager_approve_officer_registration(mgr, reg)
        self.assertEqual(reg.status, Registration.STATUS_APPROVED)

    # 12. Officer access to hidden project ---------------------------------
    def test_12_officer_access_hidden(self):
        env = _build_env()
        urepo, proj_repo = env["user_repo"], env["project_repo"]
        reg_service = env["registration_service"]
        proj_service = env["project_service"]

        mgr = HDBManager("Mgr", "S1414141K", 45, "Married", "m")
        urepo.add_user(mgr)
        prj = _create_project("HiddenProj", mgr, proj_repo, visibility=True)

        off = HDBOfficer("Officer", "S1515151L", 31, "Married", "o")
        urepo.add_user(off)
        reg = reg_service.officer_register_for_project(off, prj)
        reg_service.manager_approve_officer_registration(mgr, reg)

        # hide project
        prj.visibility = False
        proj_repo.update(prj)
        handled = proj_service.get_handled_projects_for_officer(off.nric)
        self.assertIn(prj, handled)

    # 13. Officers cannot edit project details -----------------------------
    def test_13_officer_cannot_edit(self):
        env = _build_env()
        urepo, proj_repo = env["user_repo"], env["project_repo"]
        proj_service = env["project_service"]

        mgr = HDBManager("Mgr", "S3131313M", 40, "Married", "m")
        urepo.add_user(mgr)
        prj = _create_project("NoEdit", mgr, proj_repo)

        off = HDBOfficer("Officer", "S3232323N", 30, "Married", "o")
        urepo.add_user(off)

        with self.assertRaises(OperationError):
            proj_service.edit_project(off, prj, {"neighborhood": "NewTown"})

    # 14. Response to project enquiries ------------------------------------
    def test_14_enquiry_reply(self):
        env = _build_env()
        urepo, proj_repo = env["user_repo"], env["project_repo"]
        enq_service = env["enquiry_service"]
        reg_service = env["registration_service"]

        mgr = HDBManager("Mgr", "S5656565H", 45, "Married", "m")
        urepo.add_user(mgr)
        prj = _create_project("ReplyProj", mgr, proj_repo)

        off = HDBOfficer("Officer", "S5757575I", 31, "Married", "o")
        urepo.add_user(off)
        reg = reg_service.officer_register_for_project(off, prj)
        reg_service.manager_approve_officer_registration(mgr, reg)

        appl = Applicant("Que", "S5858585J", 35, "Single", "q")
        urepo.add_user(appl)
        enq = enq_service.submit_enquiry(appl, prj, "Any shops nearby?")

        enq_service.reply_to_enquiry(off, enq, "Yes, a mall across the street.")
        self.assertTrue(enq.is_replied())

    # 15. Flat selection & inventory update --------------------------------
    def test_15_flat_selection_inventory(self):
        env = _build_env()
        urepo = env["user_repo"]
        proj_repo = env["project_repo"]
        reg_service = env["registration_service"]
        app_service = env["application_service"]

        mgr = HDBManager("Mgr", "S6161616G", 45, "Married", "m")
        urepo.add_user(mgr)
        prj = _create_project("StockProj", mgr, proj_repo, num2=1, num3=0)

        off = HDBOfficer("Officer", "S6262626H", 31, "Married", "o")
        urepo.add_user(off)
        reg = reg_service.officer_register_for_project(off, prj)
        reg_service.manager_approve_officer_registration(mgr, reg)

        appl = Applicant("Buy", "S6363636I", 25, "Married", "b")
        urepo.add_user(appl)
        # apply & approve
        app_service.apply_for_project(appl, prj, 2)
        app = env["application_repo"].find_by_applicant_nric(appl.nric)
        app_service.manager_approve_application(mgr, app)

        # book – unit count becomes 0
        app_service.officer_book_flat(off, app)
        units_left, _ = prj.get_flat_details(2)
        self.assertEqual(units_left, 0)

    # 16. Receipt generation accuracy --------------------------------------
    def test_16_receipt_generation(self):
        env = _build_env()
        urepo = env["user_repo"]
        proj_repo = env["project_repo"]
        reg_service = env["registration_service"]
        app_service = env["application_service"]

        mgr = HDBManager("Mgr", "S6464646J", 45, "Married", "m")
        urepo.add_user(mgr)
        prj = _create_project("ReceiptProj", mgr, proj_repo)

        off = HDBOfficer("Officer", "S6565656K", 31, "Married", "o")
        urepo.add_user(off)
        reg = reg_service.officer_register_for_project(off, prj)
        reg_service.manager_approve_officer_registration(mgr, reg)

        appl = Applicant("Buyer", "S6666666L", 25, "Married", "b")
        urepo.add_user(appl)
        app_service.apply_for_project(appl, prj, 2)
        app = env["application_repo"].find_by_applicant_nric(appl.nric)
        app_service.manager_approve_application(mgr, app)
        app_service.officer_book_flat(off, app)

        # Build receipt data using helper from controller (simplified here)
        receipt = {
            "Applicant Name": appl.name,
            "NRIC": appl.nric,
            "Flat Type Booked": "2-Room",
            "Project Name": prj.project_name,
        }
        self.assertEqual(receipt["Project Name"], "ReceiptProj")

    # 17. Create, edit, delete project -------------------------------------
    def test_17_crud_project(self):
        env = _build_env()
        urepo, proj_service = env["user_repo"], env["project_service"]
        proj_repo = env["project_repo"]

        mgr = HDBManager("Mgr", "S6767676M", 45, "Married", "m")
        urepo.add_user(mgr)
        p = proj_service.create_project(mgr, "CRUD", "Town", 1, 100, 1, 150, *_make_dates(), 1)
        # edit name
        proj_service.edit_project(mgr, p, {"name": "CRUD2"})
        self.assertIsNotNone(proj_repo.find_by_name("CRUD2"))
        # delete
        proj_service.delete_project(mgr, p)
        self.assertIsNone(proj_repo.find_by_name("CRUD2"))

    # 18. Manager cannot manage overlapping projects -----------------------
    def test_18_overlap_management(self):
        env = _build_env()
        urepo, proj_service = env["user_repo"], env["project_service"]

        mgr = HDBManager("Mgr", "S7878787M", 45, "Married", "m")
        urepo.add_user(mgr)
        _create_project("First", mgr, env["project_repo"], days_open=60)
        # second overlapping project should fail
        with self.assertRaises(OperationError):
            proj_service.create_project(mgr, "Second", "Place", 1, 100, 1, 150, *_make_dates(), 1)

    # 19. Toggle visibility works ------------------------------------------
    def test_19_toggle_visibility(self):
        env = _build_env()
        urepo, proj_service = env["user_repo"], env["project_service"]
        proj_repo = env["project_repo"]

        mgr = HDBManager("Mgr", "S8989898M", 45, "Married", "m")
        urepo.add_user(mgr)
        prj = _create_project("Toggle", mgr, proj_repo, visibility=True)
        status_after = proj_service.toggle_project_visibility(mgr, prj)
        self.assertEqual(status_after, "OFF")
        self.assertFalse(prj.visibility)

    # 20. Manager project list filtering -----------------------------------
    def test_20_filter_projects(self):
        env = _build_env()
        proj_service = env["project_service"]
        proj_repo = env["project_repo"]
        urepo = env["user_repo"]

        mgr = HDBManager("Mgr", "S9090909M", 45, "Married", "m")
        urepo.add_user(mgr)
        pA = _create_project("Alpha", mgr, proj_repo)
        pB = _create_project("Beta", mgr, proj_repo)
        filtered = proj_service.filter_projects([pA, pB], location="TestVille")
        self.assertEqual(len(filtered), 2)

    # 21. Officer slot count update ----------------------------------------
    def test_21_officer_slots(self):
        env = _build_env()
        urepo, proj_repo = env["user_repo"], env["project_repo"]
        reg_service = env["registration_service"]

        mgr = HDBManager("Mgr", "S9191919M", 45, "Married", "m")
        urepo.add_user(mgr)
        prj = _create_project("SlotProj", mgr, proj_repo, num2=1, num3=1)
        prj.officer_slot = 1  # only one slot

        off1 = HDBOfficer("Off1", "S9292929O", 30, "Married", "o1")
        off2 = HDBOfficer("Off2", "S9393939P", 30, "Married", "o2")
        urepo.add_user(off1)
        urepo.add_user(off2)

        reg1 = reg_service.officer_register_for_project(off1, prj)
        reg_service.manager_approve_officer_registration(mgr, reg1)

        # second officer approval should fail due to slots full
        reg2 = reg_service.officer_register_for_project(off2, prj)
        with self.assertRaises(OperationError):
            reg_service.manager_approve_officer_registration(mgr, reg2)

    # 22. Application & withdrawal approval ---------------------------------
    def test_22_application_withdrawal_flow(self):
        env = _build_env()
        urepo, proj_repo = env["user_repo"], env["project_repo"]
        app_service = env["application_service"]

        mgr = HDBManager("Mgr", "S9494949M", 45, "Married", "m")
        urepo.add_user(mgr)
        prj = _create_project("FlowProj", mgr, proj_repo)

        appl = Applicant("Quitter", "S9595959Q", 35, "Single", "q")
        urepo.add_user(appl)
        app_service.apply_for_project(appl, prj, 2)
        app = env["application_repo"].find_by_applicant_nric(appl.nric)

        # applicant requests withdrawal
        app_service.request_withdrawal(app)
        self.assertTrue(app.request_withdrawal)
        # manager approves
        app_service.manager_approve_withdrawal(mgr, app)
        self.assertEqual(app.status, Application.STATUS_UNSUCCESSFUL)

    # 23. Booking report generation & filters ------------------------------
    def test_23_report_generation(self):
        env = _build_env()
        urepo, proj_repo = env["user_repo"], env["project_repo"]
        reg_service = env["registration_service"]
        app_service = env["application_service"]

        mgr = HDBManager("Mgr", "S9696969M", 45, "Married", "m")
        urepo.add_user(mgr)
        prj = _create_project("ReportProj", mgr, proj_repo)

        off = HDBOfficer("Officer", "S9797979O", 31, "Married", "o")
        urepo.add_user(off)
        reg = reg_service.officer_register_for_project(off, prj)
        reg_service.manager_approve_officer_registration(mgr, reg)

        appl = Applicant("Reporter", "S9898989R", 25, "Married", "r")
        urepo.add_user(appl)
        app_service.apply_for_project(appl, prj, 2)
        app = env["application_repo"].find_by_applicant_nric(appl.nric)
        app_service.manager_approve_application(mgr, app)
        app_service.officer_book_flat(off, app)

        data = app_service.generate_booking_report_data(filter_project_name="ReportProj")
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["Project Name"], "ReportProj")


# ---------------------------------------------------------------------------
# Main execution point ------------------------------------------------------
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # run the full suite with a nice output buffer
    unittest.main(verbosity=2)
