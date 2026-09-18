import { BrowserRouter, Routes, Route } from "react-router-dom";
import Nav from "./components/Nav";
import Dashboard from "./pages/Dashboard";
import NewMeeting from "./pages/NewMeeting";
import Meetings from "./pages/Meetings";
import Jobs from "./pages/Jobs";
import MeetingDetail from "./pages/MeetingDetail";
import Settings from "./pages/Settings";
import SystemStatus from "./pages/SystemStatus";
import Search from "./pages/Search";

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <Nav />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/new-meeting" element={<NewMeeting />} />
            <Route path="/meetings" element={<Meetings />} />
            <Route path="/meetings/:meetingId" element={<MeetingDetail />} />
            <Route path="/jobs" element={<Jobs />} />
            <Route path="/search" element={<Search />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/system-status" element={<SystemStatus />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
