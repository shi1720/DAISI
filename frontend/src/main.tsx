import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import '@fontsource/dm-sans/latin-400.css';
import '@fontsource/dm-sans/latin-600.css';
import '@fontsource/manrope/latin-400.css';
import '@fontsource/manrope/latin-600.css';
import '@fontsource/manrope/latin-700.css';
import 'leaflet/dist/leaflet.css';
import './styles.css';

class ErrorBoundary extends React.Component<React.PropsWithChildren, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    return this.state.failed ? <main className="fatal-screen"><h1>Let’s reconnect the desk.</h1><p>The page encountered an unexpected error. Your saved plans are still on the server.</p><button className="button primary" onClick={() => location.reload()}>Reload HawkerBridge</button></main> : this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><ErrorBoundary><App /></ErrorBoundary></React.StrictMode>);
