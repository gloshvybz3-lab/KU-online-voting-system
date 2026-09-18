"""
Kampala University Online Voting System (KU-OVS)
Comprehensive Database Seed Script
Populates authoritative university records, students, administrators,
elections, contested offices, eligibility criteria, and realistic candidates.
"""

from datetime import datetime, timedelta
from app import create_app
from models import (
    db, UniversityRecord, Student, Admin, Election, Position,
    Candidate, EligibilityRule, Notification, FAQ, utc_now
)

app = create_app()

def seed_database():
    with app.app_context():
        print("[KU-OVS] Recreating and seeding database...")
        db.create_all()

        # --------------------------------------------------------------------------
        # 1. Clear Existing Data (for clean seed)
        # --------------------------------------------------------------------------
        db.session.query(Notification).delete()
        db.session.query(FAQ).delete()
        db.session.query(Candidate).delete()
        db.session.query(EligibilityRule).delete()
        db.session.query(Position).delete()
        db.session.query(Election).delete()
        db.session.query(Admin).delete()
        db.session.query(Student).delete()
        db.session.query(UniversityRecord).delete()
        db.session.commit()

        # --------------------------------------------------------------------------
        # 2. Authoritative University Registrar Records
        # --------------------------------------------------------------------------
        print(" -> Seeding University Registrar records...")
        raw_registrar_data = [
            # Ggaba Main Campus
            ("KU/2024/001", "24/KU/001/UG", "Mukasa Denis", "denis.mukasa@ku.ac.ug", "Ggaba (Main Campus)", "Faculty of Computer Science and Information Technology", "Bachelor of Information Technology", 2, "Male"),
            ("KU/2024/002", "24/KU/002/UG", "Acheng Sarah", "sarah.acheng@ku.ac.ug", "Ggaba (Main Campus)", "Faculty of Computer Science and Information Technology", "Bachelor of Computer Science", 2, "Female"),
            ("KU/2023/015", "23/KU/015/UG", "Kintu Ronald", "ronald.kintu@ku.ac.ug", "Ggaba (Main Campus)", "Faculty of Business Administration & Management", "Bachelor of Business Administration", 3, "Male"),
            ("KU/2023/016", "23/KU/016/UG", "Nalubega Patricia", "patricia.nalubega@ku.ac.ug", "Ggaba (Main Campus)", "Faculty of Business Administration & Management", "Bachelor of Commerce", 3, "Female"),
            ("KU/2025/080", "25/KU/080/UG", "Otim Daniel", "daniel.otim@ku.ac.ug", "Ggaba (Main Campus)", "Faculty of Education", "Bachelor of Education (Arts)", 1, "Male"),

            # Old Kampala Campus
            ("KU/2024/020", "24/KU/020/UG", "Namutebi Fatuma", "fatuma.namutebi@ku.ac.ug", "Old Kampala Campus", "Faculty of Business Administration & Management", "Bachelor of Business Administration", 2, "Female"),
            ("KU/2024/021", "24/KU/021/UG", "Ssemwogerere Paul", "paul.ssemwogerere@ku.ac.ug", "Old Kampala Campus", "Faculty of Arts & Social Sciences", "Bachelor of Mass Communication", 2, "Male"),
            ("KU/2023/045", "23/KU/045/UG", "Alinda Miriam", "miriam.alinda@ku.ac.ug", "Old Kampala Campus", "Faculty of Education", "Bachelor of Education (Science)", 3, "Female"),

            # Luweero Campus
            ("KU/2024/030", "24/KU/030/UG", "Kavuma Isaac", "isaac.kavuma@ku.ac.ug", "Luweero Campus", "Faculty of Education", "Bachelor of Education (Primary)", 2, "Male"),
            ("KU/2024/031", "24/KU/031/UG", "Nansubuga Ritah", "ritah.nansubuga@ku.ac.ug", "Luweero Campus", "Faculty of Arts & Social Sciences", "Bachelor of Development Studies", 2, "Female"),
            ("KU/2023/060", "23/KU/060/UG", "Muwonge Derrick", "derrick.muwonge@ku.ac.ug", "Luweero Campus", "Faculty of Computer Science and Information Technology", "Bachelor of Information Technology", 3, "Male"),

            # Jinja Campus
            ("KU/2024/040", "24/KU/040/UG", "Waiswa Kenneth", "kenneth.waiswa@ku.ac.ug", "Jinja Campus", "Faculty of Business Administration & Management", "Bachelor of Procurement & Logistics", 2, "Male"),
            ("KU/2024/041", "24/KU/041/UG", "Babirye Sandra", "sandra.babirye@ku.ac.ug", "Jinja Campus", "Faculty of Computer Science and Information Technology", "Bachelor of Computer Science", 2, "Female"),

            # Masaka Campus
            ("KU/2024/050", "24/KU/050/UG", "Ssenyonga Moses", "moses.ssenyonga@ku.ac.ug", "Masaka Campus", "Faculty of Health Sciences", "Bachelor of Public Health", 2, "Male"),
            ("KU/2024/051", "24/KU/051/UG", "Nakimuli Diana", "diana.nakimuli@ku.ac.ug", "Masaka Campus", "Faculty of Health Sciences", "Bachelor of Nursing Science", 2, "Female")
        ]

        uni_records = []
        for sid, reg, name, email, campus, faculty, course, yr, gender in raw_registrar_data:
            rec = UniversityRecord(
                student_id=sid,
                reg_no=reg,
                full_name=name,
                email=email,
                campus=campus,
                faculty=faculty,
                course=course,
                year_of_study=yr,
                gender=gender,
                is_registered_student=True
            )
            uni_records.append(rec)
            db.session.add(rec)
        db.session.commit()

        # --------------------------------------------------------------------------
        # 3. Pre-register Verified Students
        # All have password: Student@2026
        # --------------------------------------------------------------------------
        print(" -> Registering verified student voters...")
        for rec in uni_records:
            student = Student(
                student_id=rec.student_id,
                reg_no=rec.reg_no,
                full_name=rec.full_name,
                email=rec.email,
                campus=rec.campus,
                faculty=rec.faculty,
                course=rec.course,
                year_of_study=rec.year_of_study,
                gender=rec.gender,
                is_verified=True,
                is_active=True
            )
            student.set_password("Student@2026")
            db.session.add(student)
        db.session.commit()

        # --------------------------------------------------------------------------
        # 4. Electoral Commission & Administrators
        # --------------------------------------------------------------------------
        print(" -> Seeding Electoral Commission accounts...")
        # System Admin
        admin1 = Admin(
            username="admin",
            email="admin@ku.ac.ug",
            full_name="Prof. Badru Dungu (ICT Director)",
            role="super_admin",
            is_active=True
        )
        admin1.set_password("Admin@KU2026")
        db.session.add(admin1)

        # EC Chairperson
        admin2 = Admin(
            username="ec_chair",
            email="ec_chair@ku.ac.ug",
            full_name="Dr. Hajjat Aisha Nakanwagi (EC Chair)",
            role="ec_chair",
            is_active=True
        )
        admin2.set_password("Chair@KU2026")
        db.session.add(admin2)

        # Commissioner
        admin3 = Admin(
            username="commissioner1",
            email="returning.officer@ku.ac.ug",
            full_name="Mr. James Opolot (Returning Officer)",
            role="ec_commissioner",
            is_active=True
        )
        admin3.set_password("Comm@KU2026")
        db.session.add(admin3)
        db.session.commit()

        # --------------------------------------------------------------------------
        # 5. Elections
        # --------------------------------------------------------------------------
        print(" -> Creating elections and contested positions...")
        now = utc_now()

        # Active Election (Open for voting right now)
        active_election = Election(
            title="Kampala University Guild & Campus Representative Elections 2025/2026",
            description="Official annual student elections for the Guild Presidency, Campus Representatives, and Faculty Representatives across all Kampala University constituent campuses.",
            academic_year="2025/2026",
            start_time=now - timedelta(hours=2),
            end_time=now + timedelta(hours=22),
            status="active",
            created_by=admin1.id
        )
        db.session.add(active_election)
        db.session.commit()

        # Past Election with Certified Published Results
        published_election = Election(
            title="Kampala University Guild By-Elections 2024/2025",
            description="Constitutional by-elections to fill vacant student leadership portfolios.",
            academic_year="2024/2025",
            start_time=now - timedelta(days=90),
            end_time=now - timedelta(days=89),
            status="results_published",
            results_approved_by=admin2.id,
            results_approved_at=now - timedelta(days=88),
            created_by=admin1.id
        )
        db.session.add(published_election)
        db.session.commit()

        # --------------------------------------------------------------------------
        # 6. Contested Positions & Eligibility Rules for Active Election
        # --------------------------------------------------------------------------
        # Pos 1: Guild President (Universal: ALL campuses & faculties)
        p1 = Position(
            election_id=active_election.id,
            title="Guild President",
            description="Chief executive leader of the Kampala University Guild Government representing the entire student body.",
            priority_order=1
        )
        db.session.add(p1)
        db.session.commit()
        # Rule: Universal
        db.session.add(EligibilityRule(election_id=active_election.id, position_id=p1.id, campus="ALL", faculty="ALL", course="ALL", year_of_study=0, gender="ALL"))

        # Pos 2: Vice Guild President (Universal: ALL campuses & faculties)
        p2 = Position(
            election_id=active_election.id,
            title="Vice Guild President",
            description="Principal deputy to the Guild President and coordinator of campus guild committees.",
            priority_order=2
        )
        db.session.add(p2)
        db.session.commit()
        db.session.add(EligibilityRule(election_id=active_election.id, position_id=p2.id, campus="ALL", faculty="ALL", course="ALL", year_of_study=0, gender="ALL"))

        # Pos 3: Ggaba Main Campus Representative (Only Ggaba Campus students)
        p3 = Position(
            election_id=active_election.id,
            title="Ggaba Main Campus Representative",
            description="Advocate for student welfare and facility matters at the Ggaba Main Campus.",
            priority_order=3
        )
        db.session.add(p3)
        db.session.commit()
        db.session.add(EligibilityRule(election_id=active_election.id, position_id=p3.id, campus="Ggaba (Main Campus)", faculty="ALL", course="ALL", year_of_study=0, gender="ALL"))

        # Pos 4: Luweero Campus Representative (Only Luweero Campus students)
        p4 = Position(
            election_id=active_election.id,
            title="Luweero Campus Representative",
            description="Advocate for student welfare at the Luweero Campus.",
            priority_order=4
        )
        db.session.add(p4)
        db.session.commit()
        db.session.add(EligibilityRule(election_id=active_election.id, position_id=p4.id, campus="Luweero Campus", faculty="ALL", course="ALL", year_of_study=0, gender="ALL"))

        # Pos 5: Faculty of Computer Science & IT Representative
        p5 = Position(
            election_id=active_election.id,
            title="Faculty Representative: Computer Science & IT",
            description="Academic representative representing students in Computing, IT, and Software courses.",
            priority_order=5
        )
        db.session.add(p5)
        db.session.commit()
        db.session.add(EligibilityRule(election_id=active_election.id, position_id=p5.id, campus="ALL", faculty="Faculty of Computer Science and Information Technology", course="ALL", year_of_study=0, gender="ALL"))

        # Pos 6: Female Affairs Minister
        p6 = Position(
            election_id=active_election.id,
            title="Guild Minister for Female Affairs",
            description="Minister overseeing female student affairs, mentorship, health, and campus safety.",
            priority_order=6
        )
        db.session.add(p6)
        db.session.commit()
        db.session.add(EligibilityRule(election_id=active_election.id, position_id=p6.id, campus="ALL", faculty="ALL", course="ALL", year_of_study=0, gender="Female"))
        db.session.commit()

        # --------------------------------------------------------------------------
        # 7. Candidates
        # --------------------------------------------------------------------------
        print(" -> Registering candidates with manifestos and symbols...")
        candidates_data = [
            # Guild President Candidates
            (p1.id, "Kato Jonathan", "Bachelor of Business Administration", "Ggaba (Main Campus)", "Clock", "Timely service, transparent financial accountability, and reliable high-speed campus Wi-Fi for all students.", "approved"),
            (p1.id, "Namukasa Brenda", "Bachelor of Information Technology", "Old Kampala Campus", "Book", "Digital university services, student welfare bursaries, and expanded library electronic access 24/7.", "approved"),
            (p1.id, "Okello David", "Bachelor of Computer Science", "Luweero Campus", "Lion", "Fearless student representation, decentralized campus equipment, and fair exam scheduling.", "approved"),

            # Vice Guild President Candidates
            (p2.id, "Akello Grace", "Bachelor of Education", "Jinja Campus", "Tree", "Promoting cross-campus unity, career internship placements, and vibrant sports galas.", "approved"),
            (p2.id, "Musoke Brian", "Bachelor of Commerce", "Ggaba (Main Campus)", "Star", "Student leadership excellence, transparent budget reporting, and student health insurance.", "approved"),

            # Ggaba Main Campus Rep Candidates
            (p3.id, "Nsubuga Samuel", "Bachelor of Information Technology", "Ggaba (Main Campus)", "Key", "Renovation of computer labs and round-the-clock hostel security.", "approved"),
            (p3.id, "Nakato Sarah", "Bachelor of Business Administration", "Ggaba (Main Campus)", "Sun", "Equitable student guild resource allocation and cafeteria price caps.", "approved"),

            # Luweero Campus Rep Candidates
            (p4.id, "Kigozi Peter", "Bachelor of Education (Primary)", "Luweero Campus", "Torch", "Reliable campus internet and timely delivery of exam transcripts.", "approved"),
            (p4.id, "Namubiru Rebecca", "Bachelor of Development Studies", "Luweero Campus", "Dove", "Promoting community outreach and modern nursing facility on campus.", "approved"),

            # Faculty of CS & IT Rep Candidates
            (p5.id, "Byaruhanga Ivan", "Bachelor of Computer Science", "Ggaba (Main Campus)", "Laptop", "High-spec programming workstations and cloud computing workshops.", "approved"),
            (p5.id, "Nalwanga Christine", "Bachelor of Information Technology", "Ggaba (Main Campus)", "Shield", "Bridging the tech gender gap, hackathons, and industrial tech linkages.", "approved"),

            # Female Affairs Minister Candidates
            (p6.id, "Tumusiime Brenda", "Bachelor of Mass Communication", "Old Kampala Campus", "Flower", "Women leadership forums, sanitary hygiene kits in all campus washrooms.", "approved"),
            (p6.id, "Atuhaire Mercy", "Bachelor of Public Health", "Masaka Campus", "Heart", "Accessible health screening, mental health wellness days, and women empowerment.", "approved")
        ]

        for pos_id, name, course, campus, sym_name, manifesto, status in candidates_data:
            cand = Candidate(
                election_id=active_election.id,
                position_id=pos_id,
                full_name=name,
                course=course,
                campus=campus,
                symbol_name=sym_name,
                manifesto=manifesto,
                status=status
            )
            db.session.add(cand)
        db.session.commit()

        # Positions and Candidates for the Published Past Election
        past_pos = Position(
            election_id=published_election.id,
            title="Guild Speaker By-Election",
            description="By-election to elect the Guild Parliament Speaker.",
            priority_order=1
        )
        db.session.add(past_pos)
        db.session.commit()

        c_past1 = Candidate(
            election_id=published_election.id,
            position_id=past_pos.id,
            full_name="Ssebaggala Ronald",
            course="Bachelor of Laws",
            campus="Ggaba (Main Campus)",
            symbol_name="Gavel",
            status="approved"
        )
        c_past2 = Candidate(
            election_id=published_election.id,
            position_id=past_pos.id,
            full_name="Auma Christine",
            course="Bachelor of Arts in Economics",
            campus="Old Kampala Campus",
            symbol_name="Scale",
            status="approved"
        )
        db.session.add_all([c_past1, c_past2])
        db.session.commit()

        # --------------------------------------------------------------------------
        # 8. Notifications & Announcements
        # --------------------------------------------------------------------------
        print(" -> Posting official announcements and notices...")
        notifs = [
            Notification(
                title="POLLS OFFICIALLY OPEN: Guild & Campus Representative Elections",
                message="The Kampala University Electoral Commission declares the voting booth officially OPEN. All verified students across Ggaba, Old Kampala, Luweero, Jinja, and Masaka campuses may cast their secret ballots now.\n\nStrict ballot secrecy is in effect. Save your Participation Receipt Token after submission.",
                target_group="all",
                category="election_open",
                is_pinned=True,
                created_by=admin2.id
            ),
            Notification(
                title="Voter Verification & Registrar Data Matching Notice",
                message="Students registering their voter profile must match their official Student ID and Reg No issued by the Academic Registrar. If your record is unverified, please visit your campus registrar desk before poll closure.",
                target_group="students",
                category="announcement",
                is_pinned=False,
                created_by=admin2.id
            ),
            Notification(
                title="Code of Conduct on Campaign Silence During Polling",
                message="In accordance with Section 14 of the KU Guild Election By-laws, all physical and online campaign rallies are suspended while voting remains active. Candidate agents must respect student privacy.",
                target_group="all",
                category="announcement",
                is_pinned=False,
                created_by=admin3.id
            )
        ]
        db.session.add_all(notifs)

        # --------------------------------------------------------------------------
        # 9. Frequently Asked Questions
        # --------------------------------------------------------------------------
        print(" -> Adding voter help & FAQ entries...")
        faqs = [
            FAQ(
                category="Ballot Secrecy",
                question="How does Kampala University guarantee that my vote is 100% anonymous?",
                answer="The system implements a decoupled double-table architecture. When you cast your ballot, the system verifies your eligibility and logs your participation in Table A ('voter_participation') to prevent double voting. Simultaneously, your vote choices are stored in Table B ('votes') with absolutely NO student identifier, NO receipt hash, and NO join path back to your identity. Ballots are inserted in shuffled batch order.",
                priority_order=1
            ),
            FAQ(
                category="Eligibility",
                question="Why can't I see positions for other campuses on my ballot?",
                answer="Kampala University operates multiple campuses (Ggaba Main, Old Kampala, Luweero, Jinja, Masaka). Positions like 'Luweero Campus Representative' or 'Faculty Representative' are filtered by our rule engine so you only vote for positions in which you are an enrolled, eligible stakeholder.",
                priority_order=2
            ),
            FAQ(
                category="Double Voting",
                question="Can I change or edit my vote after submitting?",
                answer="No. To safeguard electoral integrity, once your encrypted ballot is committed, the transaction is immutable and your student account is locked against casting a second ballot in the same election.",
                priority_order=3
            ),
            FAQ(
                category="Receipts",
                question="What should I do with my Participation Receipt Token?",
                answer="Your receipt token (e.g. KU-A1B2C3D4E5F6G7H8) is proof of your voting participation. You can keep it for your personal records or test it on the 'Verify Receipt' page. It confirms your vote was counted without revealing who you selected.",
                priority_order=4
            ),
            FAQ(
                category="Results",
                question="How and when are the results published?",
                answer="Real-time tabulations are compiled on an administrative ledger. Once polls close and the Electoral Commission validates all campus returns, the EC Chairperson formally approves and publishes the official certified results to the public portal.",
                priority_order=5
            )
        ]
        db.session.add_all(faqs)
        db.session.commit()

        print(" -> Database seeded successfully!")
        print("\n========================================================")
        print("KAMPALA UNIVERSITY ONLINE VOTING SYSTEM READY")
        print("========================================================")
        print("Default Administrative Accounts:")
        print(" - Super Admin:        admin / Admin@KU2026")
        print(" - EC Chairperson:     ec_chair / Chair@KU2026")
        print(" - Returning Officer:  commissioner1 / Comm@KU2026")
        print("\nDefault Verified Test Students (Password: Student@2026):")
        print(" - Mukasa Denis:       KU/2024/001 (Ggaba Main Campus, CS&IT)")
        print(" - Acheng Sarah:       KU/2024/002 (Ggaba Main Campus, Female)")
        print(" - Namutebi Fatuma:    KU/2024/020 (Old Kampala Campus, Business)")
        print(" - Kavuma Isaac:       KU/2024/030 (Luweero Campus, Education)")
        print(" - Waiswa Kenneth:     KU/2024/040 (Jinja Campus, Procurement)")
        print(" - Ssenyonga Moses:    KU/2024/050 (Masaka Campus, Health)")
        print("========================================================\n")

if __name__ == '__main__':
    seed_database()
