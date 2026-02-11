import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

const STORAGE_KEY = 'lit_rag_lang';

const resources = {
  en: {
    translation: {
      nav: {
        home: 'Home',
        dataset: 'Dataset',
        chat: 'Chat',
        search: 'Search',
        agent: 'Agent',
        files: 'Files',
        jobs: 'Knowledge Bases',
      },
      common: {
        language: 'Language',
        english: 'English',
        german: 'Deutsch',
        all: 'All',
        sign_in: 'Sign in',
        sign_out: 'Log out',
        profile: 'Profile',
        team: 'Team',
        mcp: 'MCP',
        data_sources: 'Data sources',
        model_providers: 'Model providers',
        knowledge_bases: 'Knowledge Bases',
      },
      kb: {
        select: 'Select Knowledge Base',
        docs: 'docs',
        chunks: 'chunks',
        create_new: 'Create New Knowledge Base',
        sign_in_to_create: 'Sign in to create your own knowledge base',
      },
      chat: {
        title: 'Chat',
        querying: 'Querying: {{name}}',
        history_saved: 'History saved only in opened sessions',
        open_session: 'Open Session',
        new_session: 'New Session',
        clear_session: 'Clear Session',
        no_saved_sessions: 'No saved sessions',
        export: 'Export',
        deep_analysis: 'Deep Analysis',
        phase: 'Phase',
        topic: 'Topic',
        start_conversation: 'Start a conversation',
        ask_default: 'Ask questions about the academic literature in the demo collection',
        ask_kb: 'Ask questions about documents in "{{name}}"',
        documents: '{{documents}} documents · {{chunks}} chunks',
        references: 'References',
        details: 'Details',
        ask_question: 'Ask a question about {{name}}...',
        the_literature: 'the literature',
        session_label: 'Session {{label}}',
      },
      auth: {
        sign_in_title: 'Sign in to your account',
        create_account_title: 'Create a new account',
        continue_google: 'Continue with Google',
        continue_github: 'Continue with GitHub',
        or_continue_email: 'Or continue with email',
        name_optional: 'Name (optional)',
        email_address: 'Email address',
        password: 'Password',
        confirm_password: 'Confirm Password',
        sign_in: 'Sign in',
        create_account: 'Create account',
        dont_have_account: "Don't have an account? Sign up",
        already_have_account: 'Already have an account? Sign in',
        back_home: 'Back to home',
        password_mismatch: 'Passwords do not match',
        password_length: 'Password must be at least 8 characters',
        auth_failed: 'Authentication failed',
        oauth_failed: 'Failed to initiate OAuth',
      },
    },
  },
  de: {
    translation: {
      nav: {
        home: 'Startseite',
        dataset: 'Datensatz',
        chat: 'Chat',
        search: 'Suche',
        agent: 'Agent',
        files: 'Dateien',
        jobs: 'Wissensbasen',
      },
      common: {
        language: 'Sprache',
        english: 'Englisch',
        german: 'Deutsch',
        all: 'Alle',
        sign_in: 'Anmelden',
        sign_out: 'Abmelden',
        profile: 'Profil',
        team: 'Team',
        mcp: 'MCP',
        data_sources: 'Datenquellen',
        model_providers: 'Modellanbieter',
        knowledge_bases: 'Wissensbasen',
      },
      kb: {
        select: 'Wissensbasis auswählen',
        docs: 'Dokumente',
        chunks: 'Chunks',
        create_new: 'Neue Wissensbasis erstellen',
        sign_in_to_create: 'Anmelden, um eine eigene Wissensbasis zu erstellen',
      },
      chat: {
        title: 'Chat',
        querying: 'Abfrage: {{name}}',
        history_saved: 'Verlauf wird nur in geöffneten Sitzungen gespeichert',
        open_session: 'Sitzung öffnen',
        new_session: 'Neue Sitzung',
        clear_session: 'Sitzung leeren',
        no_saved_sessions: 'Keine gespeicherten Sitzungen',
        export: 'Exportieren',
        deep_analysis: 'Tiefenanalyse',
        phase: 'Phase',
        topic: 'Thema',
        start_conversation: 'Starte eine Unterhaltung',
        ask_default: 'Stelle Fragen zur akademischen Literatur der Demo-Sammlung',
        ask_kb: 'Stelle Fragen zu Dokumenten in "{{name}}"',
        documents: '{{documents}} Dokumente · {{chunks}} Chunks',
        references: 'Quellen',
        details: 'Details',
        ask_question: 'Stelle eine Frage zu {{name}}...',
        the_literature: 'der Literatur',
        session_label: 'Sitzung {{label}}',
      },
      auth: {
        sign_in_title: 'Melde dich bei deinem Konto an',
        create_account_title: 'Neues Konto erstellen',
        continue_google: 'Mit Google fortfahren',
        continue_github: 'Mit GitHub fortfahren',
        or_continue_email: 'Oder mit E-Mail fortfahren',
        name_optional: 'Name (optional)',
        email_address: 'E-Mail-Adresse',
        password: 'Passwort',
        confirm_password: 'Passwort bestätigen',
        sign_in: 'Anmelden',
        create_account: 'Konto erstellen',
        dont_have_account: 'Noch kein Konto? Registrieren',
        already_have_account: 'Schon ein Konto? Anmelden',
        back_home: 'Zurück zur Startseite',
        password_mismatch: 'Passwörter stimmen nicht überein',
        password_length: 'Passwort muss mindestens 8 Zeichen haben',
        auth_failed: 'Authentifizierung fehlgeschlagen',
        oauth_failed: 'OAuth konnte nicht gestartet werden',
      },
    },
  },
};

const savedLanguage = localStorage.getItem(STORAGE_KEY);
const browserLanguage = navigator.language?.toLowerCase().startsWith('de') ? 'de' : 'en';
const initialLanguage = savedLanguage || browserLanguage;

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: initialLanguage,
    fallbackLng: 'en',
    interpolation: { escapeValue: false },
  });

export function setLanguage(language: 'en' | 'de') {
  i18n.changeLanguage(language);
  localStorage.setItem(STORAGE_KEY, language);
}

export default i18n;
