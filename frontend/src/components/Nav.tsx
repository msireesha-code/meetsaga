import { NavLink } from "react-router-dom";

const links = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/new-meeting", label: "New Meeting" },
  { to: "/meetings", label: "Meetings" },
  { to: "/jobs", label: "Jobs" },
  { to: "/search", label: "Search" },
  { to: "/settings", label: "Settings" },
  { to: "/system-status", label: "System Status" },
];

export default function Nav() {
  return (
    <aside className="sidebar">
      <h1>MeetSage</h1>
      <p className="tagline">Capture. Understand. Act.</p>
      <nav>
        {links.map((l) => (
          <NavLink key={l.to} to={l.to} end={l.end} className={({ isActive }) => (isActive ? "active" : "")}>
            {l.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
