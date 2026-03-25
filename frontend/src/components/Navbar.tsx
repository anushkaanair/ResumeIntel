import { useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useThemeStore } from '../stores/themeStore';
import { Sun, Moon } from 'lucide-react';
import '../pages/HomePage.css';

/** Top navigation bar used globally. */
export function Navbar() {
  const location = useLocation();
  const isHome = location.pathname === '/';
  const isCanvasOrInterview = location.pathname.startsWith('/canvas') || location.pathname.startsWith('/interview');
  const { theme, toggleTheme } = useThemeStore();

  // Initialize data-theme attribute on mount
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  useEffect(() => {
    /* Nav CTA glow ring hover logic */
    const ncta = document.querySelector('.ncta') as HTMLElement;
    let cleanup = () => {};
    
    if (ncta) {
      let a = 0;
      let on = false;
      let raf: number | null = null;
      
      const onEnter = () => {
        on = true;
        (function s() {
          a += 1.5;
          ncta.style.setProperty('--na', a + 'deg');
          if (on) raf = requestAnimationFrame(s);
        })();
      };
      
      const onLeave = () => {
        on = false;
        if (raf) cancelAnimationFrame(raf);
      };

      ncta.addEventListener('mouseenter', onEnter);
      ncta.addEventListener('mouseleave', onLeave);

      cleanup = () => {
        ncta.removeEventListener('mouseenter', onEnter);
        ncta.removeEventListener('mouseleave', onLeave);
      }
    }
    return cleanup;
  }, [location.pathname]);

  const navStyle = isHome 
    ? {} 
    : { background: 'var(--bg2)', borderBottom: '1px solid var(--b)' };

  return (
    <nav style={navStyle}>
      <Link to="/" className="nl">
        Resume<em>Intel</em>
      </Link>
      <div className="nv">
        <Link to="/" style={{ fontSize: '.85rem', fontWeight: 600, color: 'var(--t2)', textDecoration: 'none' }}>Home</Link>
        <Link to="/canvas/demo?jdId=jd-001" style={{ fontSize: '.85rem', fontWeight: 600, color: 'var(--t2)', textDecoration: 'none' }}>Canvas</Link>
        <Link to="/interview/demo?resumeId=demo" style={{ fontSize: '.85rem', fontWeight: 600, color: 'var(--t2)', textDecoration: 'none' }}>Interview Prep</Link>
        
        {/* Theme toggle */}
        <button
          className="theme-toggle"
          onClick={toggleTheme}
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        >
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </button>

        {!(isCanvasOrInterview || location.pathname.startsWith('/optimize')) && (
          <Link to="/optimize">
            <button className="ncta">
              <div className="gr"></div>Optimize Now
            </button>
          </Link>
        )}
      </div>
    </nav>
  );
}
