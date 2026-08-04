import { Navigate, Route, Routes } from 'react-router-dom'
import CategoryListPage from './pages/CategoryListPage'
import TaskListPage from './pages/TaskListPage'
import TaskDetailPage from './pages/TaskDetailPage'

function App() {
  return (
    <div className="mx-auto flex min-h-screen w-full max-w-[480px] flex-col bg-white shadow-lg">
      <Routes>
        <Route path="/" element={<CategoryListPage />} />
        <Route path="/category/:categoryId" element={<TaskListPage />} />
        <Route
          path="/category/:categoryId/task/:taskId"
          element={<TaskDetailPage />}
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}

export default App
