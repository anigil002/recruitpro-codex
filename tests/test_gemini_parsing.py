from app.services.gemini import GeminiService


def test_extract_positions_skips_section_headings_and_bullets():
    text = """Requirements Management Lead
Years of Experience: 12-18 years
Position Overview
The Requirements Management Lead is responsible for establishing and maintaining the complete requirements framework for the LRT program, ensuring traceability from concept design through testing, commissioning, and operations. This role ensures that all project requirements—technical, functional, operational, safety, and regulatory—are captured, verified, and validated in alignment with systems engineering principles and client objectives. The Requirements Management Lead acts as the single point of accountability for requirements configuration control, change management, and compliance demonstration across all project disciplines.
Key Responsibilities
• Develop and implement the Requirements Management Plan (RMP) defining processes, tools, roles, and interfaces for managing requirements throughout the project lifecycle.
• Establish and maintain the Requirements Traceability Matrix (RTM) linking high-level project objectives to design outputs, verification evidence, and acceptance criteria.
• Ensure all requirements are structured, measurable, and verifiable, aligned with EN 50126/50128/50129 systems assurance standards.
• Coordinate with Systems Lead, Interface Manager, and Integration Manager to ensure consistent requirement flowdown to subsystems (Rolling Stock, Signaling/TSP, OCS/TPSS, Telecom/SCADA, Fare System, OMSF).
• Facilitate requirements capture workshops with stakeholders to translate operational needs into technical and functional specifications.
• Govern configuration control and change management for requirements baselines in coordination with the Configuration Manager.
• Monitor contractor compliance with requirements and verification plans; track status and deviations.
• Review and approve requirements management deliverables from design consultants and contractors.
• Ensure verification and validation (V&V) activities are linked to requirements and that all evidence is properly documented and auditable.
• Support the Safety and RAMS teams in tracing safety and performance requirements through the Safety Case and certification process.
• Develop dashboards and reporting mechanisms to track requirement completion, V&V status, and compliance performance.
• Provide training and mentorship to PMC and client teams on requirements management processes and tool usage.
• Lead readiness reviews, audits, and regulatory submissions to demonstrate compliance and system assurance.
• Coordinate with Integration and Testing teams to ensure validation test cases fully satisfy operational requirements.
• Maintain a controlled database of all project requirements and verification evidence.
"""

    service = GeminiService()
    sentences = GeminiService._split_sentences(text)

    positions = service._extract_positions(sentences, "jd.txt")

    assert [position["title"] for position in positions] == ["Requirements Management Lead"]
    assert positions[0]["responsibilities"]
