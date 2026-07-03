import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { listOrganizations } from '../api/organizations'
import { listWorkspaces } from '../api/workspaces'

const WorkspaceContext = createContext(null)

export function WorkspaceProvider({ children }) {
  const [organizations, setOrganizations] = useState([])
  const [workspaces, setWorkspaces] = useState([])
  const [currentOrg, setCurrentOrg] = useState(null)
  const [currentWorkspace, setCurrentWorkspace] = useState(null)
  const [loading, setLoading] = useState(true)

  const refreshOrganizations = useCallback((selectSlug) => {
    return listOrganizations().then((res) => {
      const orgs = res.data.items || res.data
      setOrganizations(orgs)
      if (selectSlug) {
        const match = orgs.find((o) => o.slug === selectSlug)
        if (match) setCurrentOrg(match)
      } else if (orgs.length > 0 && !currentOrg) {
        setCurrentOrg(orgs[0])
      }
      return orgs
    })
  }, [currentOrg])

  const refreshWorkspaces = useCallback((selectSlug) => {
    if (!currentOrg) return Promise.resolve([])
    return listWorkspaces(currentOrg.slug).then((res) => {
      const ws = res.data.items || res.data
      setWorkspaces(ws)
      if (selectSlug) {
        const match = ws.find((w) => w.slug === selectSlug)
        if (match) setCurrentWorkspace(match)
      } else if (ws.length > 0 && !currentWorkspace) {
        setCurrentWorkspace(ws[0])
      }
      return ws
    })
  }, [currentOrg, currentWorkspace])

  useEffect(() => {
    refreshOrganizations().finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!currentOrg) return
    setCurrentWorkspace(null)
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
        refreshOrganizations,
        refreshWorkspaces,
        loading,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  )
}

export const useWorkspace = () => useContext(WorkspaceContext)