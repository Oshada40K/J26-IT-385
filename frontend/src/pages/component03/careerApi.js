export const ENDPOINTS = {
  bestJob: '/api/career/best-job',
  topJobs: '/api/career/top-jobs',
  explanation: '/api/career/explanation',
}

export function describeCareerError(error, baseUrl) {
  if (error instanceof TypeError) return `Unable to connect to backend at ${baseUrl}.`
  const match = /^API error (\d+): ([\s\S]*)$/.exec(error?.message || '')
  if (match) {
    try {
      const detail = JSON.parse(match[2]).detail
      if (detail) return `HTTP ${match[1]}: ${typeof detail === 'string' ? detail : JSON.stringify(detail)}`
    } catch { /* Show the original response if it is not JSON. */ }
  }
  return error?.message || 'Unknown error'
}

export async function getCareerResult(key, baseUrl, session) {
  const query = session?.candidate_id && session?.access_token
    ? `?${new URLSearchParams({ candidate_id: session.candidate_id })}` : ''
  const headers = query ? { Authorization: `Bearer ${session.access_token}` } : {}
  const response = await fetch(`${baseUrl}${ENDPOINTS[key]}${query}`, { headers })
  if (!response.ok) throw new Error(`API error ${response.status}: ${await response.text()}`)
  const data = await response.json()
  if (query && data.candidate_id !== session.candidate_id) {
    if (data.candidate_id === 'sample_candidate_001') {
      throw new Error(`The backend at ${baseUrl} returned a sample recommendation instead of your CV result. Deploy the updated Component 3 backend with candidate_id support, then reload recommendations.`)
    }
    throw new Error('The backend returned a recommendation for another candidate. Your results were not displayed. Check that the backend uses the uploaded CV candidate ID.')
  }
  return data
}

export async function getAllCareerResults(baseUrl, session) {
  const entries = await Promise.all(Object.keys(ENDPOINTS).map(async key => {
    try {
      return [key, { loading: false, data: await getCareerResult(key, baseUrl, session), error: null }]
    } catch (error) {
      return [key, { loading: false, data: null, error: describeCareerError(error, baseUrl) }]
    }
  }))
  return Object.fromEntries(entries)
}

export async function uploadAndPredictCV(file, { uploadCV, savedSession, baseUrl, onAssessed }) {
  const assessment = await uploadCV(file)
  const session = savedSession()
  if (assessment.status !== 'completed' || !session?.access_token ||
      !session?.candidate_id || assessment.candidate_id !== session.candidate_id) {
    throw new Error('A completed CV assessment and matching candidate session are required.')
  }
  onAssessed?.()
  const careerResults = await getAllCareerResults(baseUrl, session)
  return { candidateId: assessment.candidate_id, assessmentId: assessment.assessment_id, careerResults }
}
