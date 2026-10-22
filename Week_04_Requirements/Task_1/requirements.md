# Software requirements

## Priority scale

- **High**: Essential, explicitly mandatory, or stakeholder-marked high priority.
- **Medium**: Important capability without evidence that it is essential.
- **Low**: Optional or explicitly deferred enhancement.

## Sources

- `conversations/conv_pines014_material_volume.eml` (4308 characters)
- `conversations/conv_pines015_capacity_interface.eml` (3969 characters)
- `conversations/conv_pines016_shelf_space.eml` (5078 characters)
- `conversations/conv_pines018_item_transfer.eml` (7482 characters)
- `conversations/conv_pines019_020_missing_intransit.eml` (5026 characters)
- `conversations/conv_pines021_item_purging.eml` (6137 characters)
- `conversations/conv_pines022_deletions.eml` (4757 characters)
- `conversations/conv_pines023_patron_characteristics.eml` (5083 characters)
- `conversations/conv_pines024_inactive_patrons.eml` (5694 characters)
- `early_draft_srs_galecia.txt` (29557 characters)
- `email_financial_reports.eml` (5917 characters)
- `email_report_features.eml` (5221 characters)
- `email_staff_login.eml` (4283 characters)
- `evergreen_reference_2009.txt` (9265 characters)
- `interview_cataloging_2009-05-08.txt` (5900 characters)
- `interview_sysadmin_2009-05-10.txt` (5752 characters)
- `meeting_minutes/meeting_2009-03-15_minutes.txt` (7219 characters)
- `meeting_minutes/meeting_2009-07-20_minutes.txt` (10567 characters)
- `meeting_tech_subcommittee_2009-06-30.txt` (8185 characters)
- `survey_results_2009.txt` (6135 characters)

## Requirements

### REQ-001 — Volume and Category Reporting

**Priority:** High

The system should allow generation of reports on total items, categories, and circulation metrics to support collection management and resource allocation. This requirement is essential for library staff to understand their holdings and plan accordingly. The reports should detail total items in the library, number of holds, items checked out, and include customizable categories for flexibility in reporting. Document ID: conversations/conv_pines014_material_volume.eml, conversations/conv_pines015_capacity_interface.eml, conversations/conv_pines016_shelf_space.eml.

**Sources:** `conversations/conv_pines014_material_volume.eml`, `conversations/conv_pines015_capacity_interface.eml`, `conversations/conv_pines016_shelf_space.eml`
**Candidate lineage:** C-0001

### REQ-002 — System Capacity and Branch Overview

**Priority:** High

The system must provide an interface that displays the capacity of all branches in the library system at once. This overview should include filtering capabilities, the ability to drill down into individual branch statistics, and options for color-coding based on capacity levels. Such features would greatly assist branch managers in making decisions regarding item allocation and resource management. Document ID: conversations/conv_pines015_capacity_interface.eml.

**Sources:** `conversations/conv_pines015_capacity_interface.eml`
**Candidate lineage:** C-0002

### REQ-003 — Shelf Space Utilization

**Priority:** High

The system should report and compare the percentage of total circulations, the percentage of the collection, and the percentage of total shelf space occupied for each genre and format of material. This report must be able to run at both the library and system level, thereby aiding in effective space management and collection balancing. Document ID: conversations/conv_pines016_shelf_space.eml.

**Sources:** `conversations/conv_pines016_shelf_space.eml`
**Candidate lineage:** C-0003

### REQ-004 — Item Transfer Utility

**Priority:** High

There should be a utility for transferring batches of items between branches, to facilitate the movement of books for mobile libraries or outreach programs. This utility must allow for querying of candidate materials, saving of queries for future use, manual selection of titles, and updating of item locations. Additionally, items should be able to revert back to their original locations based on configurable criteria. Document ID: conversations/conv_pines018_item_transfer.eml.

**Sources:** `conversations/conv_pines018_item_transfer.eml`
**Candidate lineage:** C-0004

### REQ-005 — Missing and Damaged Items Report

**Priority:** High

The system must provide reports of missing and damaged items, allowing for inventory tracking and collection health monitoring. Additionally, an in-transit items report is needed to show items that have been in transit for more than a configurable number of days. This feature will give staff insight into potential item losses and look into transportation efficiency. Document ID: conversations/conv_pines019_020_missing_intransit.eml.

**Sources:** `conversations/conv_pines019_020_missing_intransit.eml`
**Candidate lineage:** C-0005

### REQ-006 — Item Purging and Last Copy Reports

**Priority:** High

The system should facilitate the identification of records for purging based on customizable criteria, along with enabling reporting on the last copies of items in the system. This helps library staff manage collections effectively and avoid accidental deletion of critical items. The system must manage deletion processes safely and provide an efficient method for removing items no longer in use. Document ID: conversations/conv_pines021_item_purging.eml.

**Sources:** `conversations/conv_pines021_item_purging.eml`
**Candidate lineage:** C-0006

### REQ-007 — Record Deletions Tracking and Audit

**Priority:** High

The system must track and provide insights into record deletions to ensure accountability within the library system. Tracking should include the record type, timestamp, user who performed the deletion, and the user location. This is crucial for auditing purposes as it helps manage library records effectively. Document ID: conversations/conv_pines022_deletions.eml.

**Sources:** `conversations/conv_pines022_deletions.eml`
**Candidate lineage:** C-0007

### REQ-008 — Patron Demographics and Inactive Patrons

**Priority:** High

The system should generate reports grouped by patron demographics such as age range, zip code, county of residence, and home branch. These reports will assist in program planning, outreach initiatives, and re-engagement strategies targeting inactive patrons, which is valuable for library statistics and customer relationship management. Document ID: conversations/conv_pines023_patron_characteristics.eml, conversations/conv_pines024_inactive_patrons.eml.

**Sources:** `conversations/conv_pines023_patron_characteristics.eml`, `conversations/conv_pines024_inactive_patrons.eml`
**Candidate lineage:** C-0008

## Blacklist

No requirements were classified as conflicting or nonsensical discards.

## Review status and limitations

Refinement passes: 2 (maximum 2).
Model review judgments are not proof of semantic correctness.

- OS1: pass
- OS2: pass
- OS3: pass
- OS4: pass
- OS5: pass
- OS6: pass
- OS7: pass
- OS8: pass
- OS9: pass

- No explicit mapping between each candidate requirement and the provided environment sources beyond the listed associations; however, the draft requirements appear to comprehensively cover identified needs with source citations. Potential gaps: missing explicit resolution of conflicting items between Evergreen 1.4.0.4 gaps and PINES-specific requirements (OS7), and an explicit blacklist section populated (currently empty). Also, ensure each final requirement has a unique identifier (present in draft) and that duplicates are consolidated (draft shows consolidated items with IDs REQ-001 .. REQ-008). Actionable next steps: (1) finalize a consolidated requirements registry with OS2/OS3 identifiers, (2) populate blacklist if any conflicting/nonsensical items exist, (3) run a full trace against ALL input documents to confirm no missed constraints, (4) document gap remediation decisions and include citations to exact source items for each final requirement.
