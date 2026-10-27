import { createContext, useContext } from 'react'

// Who is logged in: { username, role, member, coach }. Set once in App.
export const MeContext = createContext(null)

export function useMe() {
  return useContext(MeContext)
}

// Mirrors the backend: managers edit anything, coaches only their own classes.
// `coach` is the class's coach id.
export function canEdit(me, coach) {
  return me.role === 'manager' || (me.role === 'coach' && coach != null && coach === me.coach)
}
