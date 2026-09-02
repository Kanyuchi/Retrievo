import { LegalLayout, Placeholder, Section, NoticeBox, SubProcessorTable } from './LegalLayout';

export default function Dpa() {
  return (
    <LegalLayout
      title="Data Processing Agreement"
      subtitle="Template summary under GDPR Art. 28"
    >
      <NoticeBox>
        This page is a template summary of our standard Data Processing Agreement (DPA), not an
        executed contract. It is not legal advice; review by counsel before relying on it. To
        request a signed copy for your organization, email{' '}
        <Placeholder>{'{{CONTACT_EMAIL}}'}</Placeholder>.
      </NoticeBox>

      <Section title="1. Parties">
        <p>
          This DPA is entered into between the customer using Humbowo (the{' '}
          <strong className="text-foreground">Controller</strong>) and{' '}
          <Placeholder>{'{{LEGAL_NAME}}'}</Placeholder>, operator of Humbowo (the{' '}
          <strong className="text-foreground">Processor</strong>).
        </p>
      </Section>

      <Section title="2. Subject matter">
        <p>
          Hosting and processing of the Controller's documents and related content for the
          purpose of retrieval-augmented search and chat, as provided by the Humbowo platform.
        </p>
      </Section>

      <Section title="3. Duration">
        <p>
          This DPA remains in effect for the duration of the Controller's subscription to
          Humbowo, and terminates automatically upon termination of that subscription and
          completion of the deletion obligations described below.
        </p>
      </Section>

      <Section title="4. Nature and purpose of processing">
        <p>
          Storage, indexing, embedding, and retrieval of uploaded documents; generation of AI
          answers, summaries, and insights in response to Controller queries; and account and
          workspace administration.
        </p>
      </Section>

      <Section title="5. Categories of data">
        <ul className="list-disc pl-5 space-y-1">
          <li>Account data: user email addresses and names.</li>
          <li>Content data: documents uploaded by the Controller and their derived embeddings.</li>
          <li>Interaction data: queries, chat messages, and generated answers.</li>
          <li>Usage metadata: logs required for operation and security.</li>
        </ul>
      </Section>

      <Section title="6. Processor obligations">
        <ul className="list-disc pl-5 space-y-1">
          <li>Process personal data only on documented instructions from the Controller.</li>
          <li>Ensure personnel with data access are bound by confidentiality obligations.</li>
          <li>
            Implement appropriate technical and organizational security measures (encryption in
            transit, access controls, EU-based hosting for storage and database).
          </li>
          <li>
            Engage sub-processors as listed below, and notify the Controller of any intended
            changes to that list so the Controller may object.
          </li>
          <li>
            Assist the Controller in responding to data subject requests and in meeting its own
            GDPR obligations.
          </li>
          <li>
            Delete or return all personal data at the end of the engagement, and permanently
            delete it upon Controller-initiated account or knowledge base deletion.
          </li>
          <li>
            Make available information reasonably necessary to demonstrate compliance and allow
            for audits, including inspections conducted by the Controller or an appointed
            auditor.
          </li>
        </ul>
      </Section>

      <Section title="7. Sub-processors">
        <p>The Processor currently engages the following sub-processors:</p>
        <SubProcessorTable />
      </Section>

      <Section title="8. Requesting a signed copy">
        <p>
          To request a countersigned copy of the full DPA for your organization, contact{' '}
          <Placeholder>{'{{CONTACT_EMAIL}}'}</Placeholder>.
        </p>
      </Section>
    </LegalLayout>
  );
}
