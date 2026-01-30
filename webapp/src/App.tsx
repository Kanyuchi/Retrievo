import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import MainNav from './components/MainNav';
import Home from './pages/Home';
import Dataset from './pages/Dataset';
import Chat from './pages/Chat';
import Search from './pages/Search';
import Agent from './pages/Agent';
import Files from './pages/Files';
import DataSources from './pages/settings/DataSources';
import ModelProviders from './pages/settings/ModelProviders';
import MCP from './pages/settings/MCP';
import Team from './pages/settings/Team';
import Profile from './pages/settings/Profile';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-background">
        <MainNav />
        <main className="pt-[72px]">
          <AnimatePresence mode="wait">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/datasets" element={<Dataset />} />
              <Route path="/chats" element={<Chat />} />
              <Route path="/searches" element={<Search />} />
              <Route path="/agents" element={<Agent />} />
              <Route path="/files" element={<Files />} />
              <Route path="/settings/data-sources" element={<DataSources />} />
              <Route path="/settings/model-providers" element={<ModelProviders />} />
              <Route path="/settings/mcp" element={<MCP />} />
              <Route path="/settings/team" element={<Team />} />
              <Route path="/settings/profile" element={<Profile />} />
            </Routes>
          </AnimatePresence>
        </main>
      </div>
    </Router>
  );
}

export default App;
