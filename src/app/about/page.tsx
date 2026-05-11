export default function AboutPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="text-3xl font-bold text-foreground">About FOIA Michigan</h1>

      <div className="mt-8 space-y-6 text-muted-foreground leading-relaxed">
        <p>
          FOIA Michigan aggregates and indexes public meeting minutes from
          government entities across the state of Michigan. Our goal is to make
          local government more transparent and accessible by providing a single,
          searchable database of meeting records.
        </p>

        <h2 className="text-xl font-semibold text-foreground">Legal Basis</h2>
        <p>
          All data on this site is sourced from publicly available government
          websites. Michigan&apos;s{" "}
          <strong>Open Meetings Act (PA 267 of 1976)</strong> requires that all
          public bodies create and maintain minutes of their meetings, and make
          those minutes available for public inspection.
        </p>
        <p>
          Under the <strong>Freedom of Information Act (PA 442 of 1976)</strong>,
          meeting minutes are public records that must be made available for
          inspection and copying upon request.
        </p>

        <h2 className="text-xl font-semibold text-foreground">Coverage</h2>
        <p>We aim to collect meeting minutes from:</p>
        <ul className="list-disc pl-6 space-y-1">
          <li>83 counties</li>
          <li>1,240 townships</li>
          <li>275 cities</li>
          <li>258 villages</li>
          <li>541 school districts</li>
          <li>56 intermediate school districts (ISDs)</li>
          <li>85+ state boards and commissions</li>
          <li>300+ special districts and authorities</li>
        </ul>

        <h2 className="text-xl font-semibold text-foreground">Data Sources</h2>
        <p>
          Meeting minutes are collected from official government websites
          including platforms like BoardDocs, Legistar, CivicClerk, CivicPlus,
          and individual agency websites. Documents are processed to extract
          searchable text, including OCR processing for scanned documents.
        </p>

        <h2 className="text-xl font-semibold text-foreground">Disclaimer</h2>
        <p>
          This is an independent project and is not affiliated with any
          government agency. While we strive for accuracy, the official source
          of record is always the originating government entity. Links to
          original documents are provided where available.
        </p>
      </div>
    </div>
  );
}
