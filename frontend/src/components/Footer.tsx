// Footer component
import { Link } from 'react-router-dom';
import '../pages/HomePage.css'; 

/** Application Footer component */
export function Footer() {
  return (
    <footer>
      <div className="flo">
        Resume<em>Intel</em>
      </div>
      <div className="fli">
        <Link to="/">Docs</Link>
        <Link to="/">API</Link>
        <Link to="/">Privacy</Link>
        <Link to="/">GitHub</Link>
      </div>
      <div className="fcp">© 2026 ResumeIntel</div>
    </footer>
  );
}
