import { Navigate, Route, Routes } from 'react-router-dom'
import CategoryListPage from './pages/CategoryListPage'
import TaskListPage from './pages/TaskListPage'
import TaskDetailPage from './pages/TaskDetailPage'

function App() {
  return (
    <div className="mx-auto min-h-full w-full max-w-[480px] bg-white shadow-sm">
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
