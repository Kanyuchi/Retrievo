import { Link } from 'react-router-dom';
import { LegalLayout, Placeholder, Section, NoticeBox, SubProcessorTable } from './LegalLayout';

export default function Privacy() {
  return (
    <LegalLayout title="Privacy Policy" subtitle="Humbowo — a product of TheNerdsInt">
      <NoticeBox>
        Template — not legal advice; review by counsel before relying on it.
      </NoticeBox>

      <Section title="Who we are">
        <p>
          Humbowo is operated by <Placeholder>{'{{LEGAL_NAME}}'}</Placeholder>,{' '}
          <Placeholder>{'{{ADDRESS}}'}</Placeholder>. For any privacy question or request,
          contact us at <Placeholder>{'{{CONTACT_EMAIL}}'}</Placeholder>.
        </p>
      </Section>

      <Section title="What we collect">
        <ul className="list-disc pl-5 space-y-1">
          <li>Account information: email address and name.</li>
          <li>Content you upload: documents added to your knowledge bases.</li>
          <li>Your queries: questions and chat messages you send to your knowledge bases.</li>
          <li>
            Usage metadata: log data such as timestamps, request counts, and basic diagnostic
            information needed to operate and secure the service.
          </li>
        </ul>
      </Section>

      <Section title="Where your data lives">
        <ul className="list-disc pl-5 space-y-1">
          <li>Application server and backups: Hetzner, Falkenstein, Germany.</li>
          <li>Database: Supabase, Frankfurt, Germany (AWS region eu-central-1).</li>
          <li>Uploaded files and object storage: MinIO, running on our own EU-based server.</li>
        </ul>
      </Section>

      <Section title="How AI processing works">
        <p>
          To generate embeddings, insights, and chat answers, the text of your documents and your
          questions is sent for processing to:
        </p>
        <ul className="list-disc pl-5 space-y-1">
          <li>
            <strong className="text-foreground">OpenAI</strong> (United States) — used for
            document embeddings and AI-generated insights.
          </li>
          <li>
            <strong className="text-foreground">xAI</strong> (United States) — used for
            generating chat answers.
          </li>
        </ul>
        <p>
          Both providers process this data under their API terms, which exclude using your data
          to train their models. Storage of your documents, vectors, and account data stays in
          the EU as described above; only the specific text needed to answer a query or build an
          embedding is transmitted to these providers at the time you upload a document or ask a
          question.
        </p>
      </Section>

      <Section title="Legal bases for processing">
        <ul className="list-disc pl-5 space-y-1">
          <li>
            <strong className="text-foreground">Performance of a contract</strong> — to provide
            the service you signed up for (storing documents, answering queries).
          </li>
          <li>
            <strong className="text-foreground">Legitimate interest</strong> — to secure,
            maintain, and improve the platform.
          </li>
        </ul>
      </Section>

      <Section title="Retention">
        <p>
          We keep your data for as long as your account or knowledge base exists. Deleting a
          knowledge base or your account permanently and immediately purges its documents,
          vector embeddings, chat history, and stored files — this is not a soft delete or a
          recoverable trash state.
        </p>
      </Section>

      <Section title="Your rights">
        <ul className="list-disc pl-5 space-y-1">
          <li>Access the personal data we hold about you.</li>
          <li>Rectify inaccurate data.</li>
          <li>
            Erasure — delete your account or a knowledge base at any time from within the app, or
            by emailing <Placeholder>{'{{CONTACT_EMAIL}}'}</Placeholder>.
          </li>
          <li>Portability of your data in a structured, machine-readable format.</li>
          <li>Lodge a complaint with your local data protection supervisory authority.</li>
        </ul>
      </Section>

      <Section title="Sub-processors">
        <p>The following third parties process data on our behalf:</p>
        <SubProcessorTable />
        <p>
          See our <Link to="/legal/dpa" className="text-primary hover:underline">Data Processing Agreement</Link>{' '}
          for the contractual terms governing these sub-processors, and our{' '}
          <Link to="/trust" className="text-primary hover:underline">Trust page</Link> for a
          plain-language summary of our EU hosting setup.
        </p>
      </Section>
    </LegalLayout>
  );
}
