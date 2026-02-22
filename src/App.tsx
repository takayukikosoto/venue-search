import { SearchPage } from './pages/SearchPage'
import { PasswordGate } from './components/auth/PasswordGate'
import { ChatBot } from './components/chat/ChatBot'

function App() {
  return (
    <PasswordGate>
      <SearchPage />
      <ChatBot />
    </PasswordGate>
  )
}

export default App
