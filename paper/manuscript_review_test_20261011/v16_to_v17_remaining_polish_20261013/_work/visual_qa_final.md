# v17 final visual verification

Final render: `_render_07`, 127 pages. All 46 pages changed relative to v16
were visually inspected in the rendering passes. For each final page,
`visual_qa_pixel_provenance.json` records the exact RGB hash and the inspected
image with identical pixels. The remaining 81 pages match previously verified
v16 page images. No unresolved clipping, missing glyphs, overlaps, or newly
introduced sparse spillover pages remain. No source or layout changes were
made after the final render. The delivered PDF has identical page content
streams to this render; only PDF page labels were added.
