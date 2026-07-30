# V4 atlas visual review notes

The V3 PNG atlas panels are useful source images, but the V3 PDF placement clipped right-side panels on many A4 pages. V4 now writes an A3 landscape atlas PDF at `results/20260730_care_failure_forensics_deep_research_packet/v4_atlas_pages_a3_landscape.pdf` with one 4x3 atlas image per page and explicit point-unit bbox margins. This proves the separate atlas packet is no longer geometrically clipped. The final V4 report PDF must still avoid reintroducing clipping when it references or thumbnails the atlas.
