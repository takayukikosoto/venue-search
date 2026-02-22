import { SearchPage } from './pages/SearchPage'
import { PasswordGate } from './components/auth/PasswordGate'

function App() {
  return (
    <PasswordGate>
      <SearchPage />
    </PasswordGate>
  )
}

export default App
