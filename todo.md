# LAMAN Todo

## ~~About Page~~ (`namefinder/templates/namefinder/about.html`) — DONE

- [x] 1. Add new paragraphs after intro (Names vs Attestations + project history)
- [x] 2. Rename "Detailed Attestations" → "Attestations and Infos" feature card
- [x] 3. Delete legacy credit sentence (Xing/Oertel)
- [x] 4. Add Nina Sole acknowledgment

## ~~Guide Page~~ (`namefinder/templates/namefinder/guide.html`) — DONE

- [x] 5. Fix "Search Fragments" card: "catalog number" → "catalog or publication number"
- [x] 6. Rewrite "Correspondence & Variants" subsection (primary/variant forms, correspondences, caveat)
- [x] 7. Update "Attestations" subsection (spelling description, TLHdig link, corpora details for DNs/PNs/GNs)
- [x] 8. Delete Milieu filter from "Using Filters" section
- [x] 9. Fix "Fragment Search" section: "catalog or publication number" + remove broken "Unknown" reference

## ~~Data Issues~~ — MOSTLY DONE

- [x] 10. **"Unknown" attestations restored** — 566 Unknown attestations imported from legacy xlsx, then the Unknown name was deleted and attestations unlinked. They now appear in the Attestations tab as unlinked records.

- [x] 11. **Fragmentary names system** — Added `is_fragmentary` flag, search toggle (hidden by default), visual marking. Data Problems page (`/data-problems/`) created for reviewing fragmentary names with possible match suggestions, keep/delete/unlink actions.

- [x] 11b. **HiTop place name attestations imported** — 20,344 attestations from HiTop xlsx, 178 new place names created. Toponym attestation hide removed from views.

- [ ] 12. **Update "Fragmentary Attestations" guide section** — Review and update guide text now that fragmentary system and attestations page are in place.

- [ ] 12b. **Review remaining fragmentary names** — ~700 fragmentary names remain in Data Problems page. Use the keep/delete/unlink tools to clean up. Some unlinked attestations may need manual reassignment to correct names.

## Search & Filtering Features

- [ ] 13. **Determinative search** — Add the ability to filter/search names by determinative. Currently no determinative filter exists on the search page. The model already has a M2M relationship (`Name.determinatives`), so this needs a new dropdown filter in the index view and template.

- [ ] 14. **Adding new determinatives** — Currently new determinatives can only be added via `/admin/`. Consider allowing authenticated users to add determinatives inline when editing a name or adding an attestation (a `DeterminativeForm` already exists in `forms.py` but isn't wired to any view).

## Data Architecture

- [ ] 15. **Variant forms: structured relationships** — Currently variant forms are stored as a plain text field. Micheluccio wants the variant logic implemented consistently across all three datasets (DNs, PNs, GNs). Consider whether to keep free-text or move to structured Name-to-Name relationships.

- [ ] 16. **Auto-classification by determinative (long-term)** — Switch GN/DN/PN classification to run automatically based on determinatives. Requires dataset coherence first across all three name types.

## Network Visualization

- [ ] 17. **Filter by name type** — Add the ability to filter network nodes by name type (Person/Place/Deity). Currently the network shows all types together with color coding but no filtering.

- [ ] 18. **Rotate the graph** — Add a rotation control for the network visualization. Currently supports zoom/pan and node dragging but no rigid rotation.

- [ ] 19. **Verbal summary of network analysis** — Generate a text summary of a name's network connections (e.g., key co-occurrences, communities, attestation contexts). Currently only a tooltip with basic stats is shown on hover.

## TLHdig Integration (Long-term)

- [ ] 20. **Semi-automatic attestation extraction from TLHdig** — Pipeline to:
  - Extract all attestations of words with determinatives (m, f, D, etc.) from TLHdig
  - Normalize spellings (merge identical consecutive letters)
  - Auto-assign normalized spellings that match existing names in the DB
  - Manually assign remaining spellings to existing names or create new ones
  - Handle enclitic chains appended to names
  - Coordinate GN treatment (Adam's HiTop data is better than TLHdig for GNs)
  - Test on current TLHdig version, then wait for upcoming major corpus update
