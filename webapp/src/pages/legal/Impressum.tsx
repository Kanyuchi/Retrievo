import { LegalLayout, Placeholder, Section } from './LegalLayout';

export default function Impressum() {
  return (
    <LegalLayout title="Impressum / Legal Notice" subtitle="Information pursuant to §5 TMG">
      <Section title="Angaben gemäß §5 TMG / Information according to §5 TMG">
        <div className="space-y-1">
          <p><Placeholder>{'{{LEGAL_NAME}}'}</Placeholder></p>
          <p><Placeholder>{'{{LEGAL_FORM}}'}</Placeholder></p>
          <p><Placeholder>{'{{ADDRESS}}'}</Placeholder></p>
        </div>
      </Section>

      <Section title="Registereintrag / Register entry">
        <div className="space-y-1">
          <p>
            Registergericht / Register court: <Placeholder>{'{{REGISTER_COURT}}'}</Placeholder>
          </p>
          <p>
            Registernummer / Register number: <Placeholder>{'{{REGISTER_NUMBER}}'}</Placeholder>
          </p>
        </div>
      </Section>

      <Section title="Umsatzsteuer-ID / VAT ID">
        <p>
          Umsatzsteuer-Identifikationsnummer gemäß §27a UStG / VAT identification number:{' '}
          <Placeholder>{'{{VAT_ID}}'}</Placeholder>
        </p>
      </Section>

      <Section title="Vertretungsberechtigt / Represented by">
        <p>
          Geschäftsführer / Managing Director: <Placeholder>{'{{MANAGING_DIRECTOR}}'}</Placeholder>
        </p>
      </Section>

      <Section title="Kontakt / Contact">
        <p>
          E-Mail / Email: <Placeholder>{'{{CONTACT_EMAIL}}'}</Placeholder>
        </p>
      </Section>

      <Section title="Streitschlichtung / Dispute resolution">
        <p>
          Die Europäische Kommission stellt eine Plattform zur Online-Streitbeilegung (OS)
          bereit. Wir sind nicht verpflichtet und nicht bereit, an einem
          Streitbeilegungsverfahren vor einer Verbraucherschlichtungsstelle teilzunehmen.
        </p>
        <p>
          The European Commission provides a platform for online dispute resolution (ODR). We
          are not obliged and not willing to participate in dispute resolution proceedings before
          a consumer arbitration board.
        </p>
      </Section>
    </LegalLayout>
  );
}
