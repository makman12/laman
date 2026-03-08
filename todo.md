# LAMAN Todo — Micheluccio's Suggested Changes

## About Page (`namefinder/templates/namefinder/about.html`)

### 1. Add new paragraphs after intro (after line 25, "...and other locations")

Insert two new paragraphs:

> *LAMAN* distinguishes between 'Names', conceived as abstract entities, and their 'Attestations' in extant manuscripts. For further details on the treatment of variant readings, correspondences between spellings and names, and scope of the data pool, please refer to the Guide.

> LAMAN was initiated by Michele Cammarosano in 2019 within the framework of the DFG-funded project *Hittite Local Cults*, with the generous support of Marco Marizza, Max Gander, Eileen Xing, and Hartmut Oertel. Since 2022, the project has been co-managed by M. Ali Akman, who transformed the initial list into a structured database and has provided fundamental improvements to the conception and planning of new features and research. With the arrival of Adam Kryszeń in 2026, the project is now poised to include the full potential of geographical names. Our trio is currently working toward the development of a fully coherent and comprehensive onomastic database of Hittite names.

---

### 2. Rename "Detailed Attestations" feature card (line 56)

**Current:**
- Label: "Detailed Attestations"
- Text: "Each name includes detailed information about where it appears, including line numbers and spellings."

**Change to:**
- Label: "Attestations and infos."
- Text: "By selecting a name, information on its occurrences (in the relevant corpora, see Guide), variant spellings, and more can be retrieved."

---

### 3. Delete legacy credit sentence (lines 77–78)

**Remove:** "Part of the LAMAN project, building on earlier work by Eileen Xing and Hartmut Oertel from a DFG-funded project on Hittite cult inventories."

(This info is now covered by the new intro paragraphs in item 1.)

---

### 4. Add Nina Sole acknowledgment (after existing acknowledgment blocks)

**Add new acknowledgment:**
> A substantial update for divine and personal names and occurrences has been carried out by Nina Sole in 2025 with funding from the project "The art of the Stage in Bronze Age Anatolia" (link: https://sites.google.com/view/ductulivesuviani/text-image-interface/the-art-of-the-stage-in-bronze-age-anatolia).

---

## Guide Page (`namefinder/templates/namefinder/guide.html`)

### 5. Fix "Search Fragments" card text (line 22)

**Current:** "Find tablets by catalog number"
**Change to:** "Find tablets by catalog or publication number"

---

### 6. Rewrite "Correspondence & Variants" subsection (lines 76–79)

**Current:**
> **Correspondence** shows how a name appears in other writing systems or languages. For example, a Hittite name might correspond to a Hurrian or Akkadian form.
> **Variant Forms** are different spellings of the same name within the Hittite corpus.

**Replace with:**
> The attested spellings are sorted into normalized name forms; when two or more normalized forms are considered to represent variants of one and the same name, one of them is taken as the "primary" form, under which all other "variant forms" are booked. "Correspondences" refer to (more or less secure and stable) relationships between names – in particular divine names – across languages and cultures. E.g., for *ALLATUM* the following correspondences are listed: Allani, EREŠ.KI.GAL, and UTU URUArinna. (Caveat: this approach is not yet fully implemented for all names and name categories!)

Keep the existing "Tip" box as-is.

---

### 7. Update "Attestations" subsection (lines 82–88)

**a)** Change the spelling description:
- **Current:** "The specific cuneiform spelling"
- **Change to:** "The attested spelling (transliteration or broad transcription; unequally implemented at present)"

**b)** Add full name for TLHdig link: "Thesaurus Linguarum Hethaeorum digitalis"

**c)** After the bullet list, add the corpora details:

> The recorded names and attestations include:
>
> **For divine names:**
> Attestations: Cuneiform tablets: KBo 42-71(1-8), ABoT 2, CHDS 2-6, DAAM 1-3, DBH 43 (Bo 8264-8485), DBH 46 (Bo 4658-Bo 5000), DBH 54 (Bo 8916-Bo 9030), UBT (Bo 8486-8694), Bo 3891 (R. Akdoğan, Kubaba 13/25, 2016); DNs from Emar: G.M. Beckman, The Pantheon of Emar, in Fs Popko, 2002.
> Names: All DNs treated in van Gessel's OHP as well as in the update.
>
> **For personal names:**
> Attestations: Cuneiform tablets: KBo 27-71(1-8), KUB 51-60; ABoT 2 (=CHDS 1); CHDS 2-6; DAAM 1-3; IBoT 4; HKM; KuSa I/1 and other fragments from Kuşaklı/Šarišsa; FHL; HTAC (= HFAC); VSNF 12; StBoTB 4; DBH 43 (Bo 8264-Bo 8485); DBH 46 (Bo 4658-Bo 5000); DBH 54 (Bo 8916-Bo 9030); UBT (Bo 8486-Bo 8694). Seals: BoHa 19 & 22; StBoTB 4; BoBe 8.
> Names: PNs attested in the above listed texts. Treatment of variant forms and correspondences in progress.
>
> **For geographical names:**
> The recorded attestations and their groupings presently correspond to the HiTop collection at HPM.

---

### 8. Delete Milieu filter from "Using Filters" section (line 164)

**Remove:** "Milieu: Cultural/linguistic background (Hittite, Hurrian, Luwian, etc.)"

---

### 9. Fix "Fragment Search" section text (lines 172–174)

**a)** Change "catalog number" → "catalog or publication number"

**b)** Remove or revise: "including fragmentary attestations linked to 'Unknown'" — this is currently not functioning correctly.

---

## Structural / Code Issues (require investigation, not just text edits)

### 10. "Unknown" attestations missing from database

Attestations previously classified as "Unknown" (fragmentary occurrences that can't be assigned to a specific name) seem to have disappeared. Example: [CHDS 2.128](https://laman.hittites.org/fragment/1241/) no longer shows the fragmentary "Piha…" occurrence.

**Action:** Investigate whether these were deleted or filtered out. Restore if feasible — Micheluccio will then manually correct assignments.

### 11. Nina Sole's fragmentary attestation entries

Nina booked fragmentary attestations as independent names rather than linking them to "Unknown". This needs manual correction by Micheluccio after item 10 is resolved.

### 12. Update "Fragmentary Attestations" guide section (lines 101–123)

Once items 10–11 are resolved and the "Unknown" system works again, review and update this section's text. The current example (CHDS 2.128) doesn't work as described.
