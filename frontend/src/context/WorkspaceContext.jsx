import { createContext, useContext, useState, useEffect } from 'react'
import { listOrganizations } from '../api/organizations'
import { listWorkspaces } from '../api/workspaces'

const WorkspaceContext = createContext(null)

export function WorkspaceProvider({ children }) {
  const [organizations, setOrganizations] = useState([])
  const [workspaces, setWorkspaces] = useState([])
  const [currentOrg, setCurrentOrg] = useState(null)
  const [currentWorkspace, setCurrentWorkspace] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    listOrganizations()
      .then((res) => {
        const orgs = res.data.items || res.data
        setOrganizations(orgs)
        if (orgs.length > 0) setCurrentOrg(orgs[0])
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!currentOrg) return
    listWorkspaces(currentOrg.slug).then((res) => {
      const ws = res.data.items || res.data
      setWorkspaces(ws)
      if (ws.length > 0) setCurrentWorkspace(ws[0])
    })
  }, [currentOrg])

  return (
    <WorkspaceContext.Provider
      value={{
        organizations,
        workspaces,
        currentOrg,
        currentWorkspace,
        setCurrentOrg,
        setCurrentWorkspace,
        loading,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  )
}

export const useWorkspace = () => useContext(WorkspaceContext)