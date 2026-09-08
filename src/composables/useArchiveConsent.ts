import { ref, watch } from 'vue'

const STORAGE_KEY = 'voice_archive_consent_v1'

export function useArchiveConsent() {
  const consented = ref(localStorage.getItem(STORAGE_KEY) === 'true')

  watch(consented, (v) => {
    if (v) localStorage.setItem(STORAGE_KEY, 'true')
    else localStorage.removeItem(STORAGE_KEY)
  })

  function grant() {
    consented.value = true
  }

  function revoke() {
    consented.value = false
  }

  return { consented, grant, revoke }
}
