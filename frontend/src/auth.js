import { createContext, useContext } from 'react'

// Who is logged in: { username, role, member, coach_name }. Set once in App.
export const MeContext = createContext(null)

export function useMe() {
  return useContext(MeContext)
}

// Mirrors the backend: managers edit anything, coaches only their own classes.
export function canEdit(me, coach) {
  return me.role === 'manager' || (me.role === 'coach' && coach === me.coach_name)
}
