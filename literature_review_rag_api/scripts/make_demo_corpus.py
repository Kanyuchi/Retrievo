"""Generate the Humbowo demo corpus: 6 synthetic papers on German regional
economic transitions, as properly line-wrapped single-page PDFs.

Facts are invented for retrieval-eval purposes; every document carries a
demo disclaimer. Usage: python scripts/make_demo_corpus.py <out_dir>
"""
import sys
import textwrap
from pathlib import Path

DISCLAIMER = ("Demo document generated for Humbowo evaluation purposes - "
              "not a real publication.")

DOCS = {
    "ruhr_coal_transition.pdf": (
        "The Ruhr Valley After Coal: Industrial Transition 1958-2018",
        """The Ruhr region of North Rhine-Westphalia was the industrial heart of
Germany, employing over 600,000 coal miners at its 1957 peak. The final
hard-coal mine, Prosper-Haniel in Bottrop, closed in December 2018, ending
160 years of deep mining in the valley.

Structural change unfolded over six decades rather than as a single shock.
The Internationale Bauausstellung Emscher Park programme of 1989 to 1999
converted industrial sites into cultural and technology parks, and the
region's universities, founded from 1962 onward, became anchors of a
knowledge economy.

By 2022 the renewable energy and environmental technology sector employed
roughly 12,000 people across the Ruhr, concentrated in green hydrogen,
building efficiency and recycling technologies. Duisburg's steel cluster
began pilot operation of hydrogen-based direct reduction in 2024.

Scholars describe the Ruhr as a case of managed decline combined with
diversification: unemployment remains above the national average, yet the
region avoided the collapse seen in comparable monostructural coalfields."""),
    "lusatia_lignite_future.pdf": (
        "Lusatia and the Lignite Phase-Out: Planning for 2038",
        """Lusatia, spanning Brandenburg and Saxony, remains Germany's largest
lignite mining district, with around 8,000 workers directly employed in
mines and power plants. Under the federal coal exit law, the last lignite
units are scheduled to close by 2038 at the latest.

The Strukturstaerkungsgesetz allocates 17 billion euros of federal
structural funds to Lusatia through 2038, financing rail connections,
research institutes and business parks intended to replace the lignite
value chain.

Unlike the Ruhr, Lusatia is sparsely populated and lacks large
universities, which researchers identify as the central risk to its
transition: new institutes such as the DLR institute in Cottbus arrived
only after 2019.

Survey evidence shows regional identity strongly tied to energy
production, and acceptance of the transition depends on visible
replacement jobs arriving before the plants close."""),
    "varieties_of_capitalism_institutions.pdf": (
        "Coordinated Market Institutions and Regional Adjustment",
        """The varieties-of-capitalism framework distinguishes liberal market
economies, which adjust through market mechanisms, from coordinated market
economies such as Germany, where firms coordinate through networks,
industry associations and collective bargaining.

Germany's dual vocational training system is the institution most often
credited with cushioning regional industrial decline: apprenticeship
pathways allow displaced industrial workers' skills to be recertified and
redirected toward growing sectors.

Codetermination through works councils shaped the sequencing of mine and
plant closures in both the Ruhr and Lusatia, producing negotiated
adjustment plans with early-retirement schemes rather than mass layoffs.

Critics argue coordinated institutions slow creative destruction and can
lock regions into declining industries; defenders reply that they preserve
social peace and skill bases that later enable diversification."""),
    "green_hydrogen_policy_nrw.pdf": (
        "Green Hydrogen Strategy in North Rhine-Westphalia",
        """North Rhine-Westphalia adopted its hydrogen roadmap in 2020, targeting
3 gigawatts of electrolyzer capacity by 2030 and positioning the Rhine-Ruhr
corridor as Europe's largest hydrogen demand cluster.

The strategy links steel decarbonization in Duisburg, chemical parks in
Marl and refinery conversion in Gelsenkirchen through a dedicated pipeline
network, with the GetH2 initiative building the first public-access
hydrogen infrastructure.

Employment studies commissioned by the state estimate up to 130,000
hydrogen-related jobs in NRW by 2050 under favorable scenarios, though
independent researchers caution that such projections assume aggressive
European demand growth.

Funding combines the federal IPCEI hydrogen program with state
instruments; the largest single grant supported thyssenkrupp's direct
reduction plant, approved at approximately 2 billion euros in 2023."""),
    "just_transition_fund_eu.pdf": (
        "The EU Just Transition Fund: Design and Allocation",
        """The Just Transition Fund, agreed in 2020 as part of the European Green
Deal, provides 19.3 billion euros for regions most affected by the move
away from fossil fuels, with Germany among the larger beneficiaries.

Access requires Territorial Just Transition Plans identifying affected
sectors, retraining needs and diversification strategies; German plans
cover Lusatia, the Rhineland lignite district and the Ruhr's remaining
coal-dependent municipalities.

The fund emphasizes retraining, small-business support and land
rehabilitation rather than large infrastructure, complementing national
structural funds that carry the heavier investments.

Evaluations note a tension between the fund's seven-year budget window
and transition timelines that span decades, raising questions about
sustained support after 2027."""),
    "labor_market_structural_change.pdf": (
        "Labor Market Outcomes of Industrial Restructuring in Germany",
        """Longitudinal studies of displaced German industrial workers find that
about 64 percent are re-employed within two years, but with average wage
losses of 10 to 15 percent that persist for a decade after displacement.

Outcomes vary sharply by age and certification: workers under forty with
recognized vocational credentials transition fastest, while workers over
fifty-five predominantly exit through early-retirement bridges negotiated
by works councils.

Regional labor market tightness matters more than individual
characteristics in several studies: identical worker profiles re-employ
faster in diversified city regions than in monostructural districts.

Active labor market programs show mixed evaluations; targeted retraining
toward certified shortage occupations outperforms general further
education, particularly for mid-career workers."""),
}


def build_pdf(title: str, body: str, out_path: Path) -> None:
    lines = [title, ""]
    for para in body.strip().split("\n\n"):
        lines.extend(textwrap.wrap(" ".join(para.split()), 78))
        lines.append("")
    lines.append(DISCLAIMER)

    def esc(s):
        return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")

    ops = "BT /F1 10 Tf 50 760 Td " + " ".join(
        f"({esc(l)}) Tj 0 -13 Td" for l in lines) + " ET"
    stream = ops.encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = b"%PDF-1.4\n"
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode()
    for off in offs:
        out += f"{off:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\n"
            f"startxref\n{xref}\n%%EOF").encode()
    out_path.write_bytes(out)


def main():
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "./demo_corpus")
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, (title, body) in DOCS.items():
        build_pdf(title, body, out_dir / name)
        print("wrote", out_dir / name)


if __name__ == "__main__":
    main()
