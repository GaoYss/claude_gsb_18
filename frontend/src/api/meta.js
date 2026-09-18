import http from './client'

export const metaApi = {
  getEnums: () => http.get('/meta/enums'),
  getTaskStandards: () => http.get('/meta/task-standards'),
  health: () => http.get('/meta/health'),
}
