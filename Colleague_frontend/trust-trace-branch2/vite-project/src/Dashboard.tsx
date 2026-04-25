import { Link } from 'react-router-dom'
import './App.css'

export default function Dashboard() {
  return (
    <>
      <section id="center">
        <h1>Dashboard</h1>
        <p>Welcome to the Dashboard page!</p>
        <p>This is your main dashboard where you can see all your data and metrics.</p>
      </section>

      <nav style={{ marginTop: '2rem', padding: '1rem', borderTop: '1px solid #ccc' }}>
        <Link to="/">Home</Link>
        {' | '}
        <Link to="/dashboard">Dashboard</Link>
      </nav>
    </>
  )
}