/**
 * LocalStorage Service
 * 
 * Provides persistent storage for chat history, structures, and images
 */

import { Message, CrystalStructure, PhononImage } from '../types'

const STORAGE_KEYS = {
  CHAT_HISTORY: 'researchmind_chat_history',
  STRUCTURES: 'researchmind_structures',
  PHONON_IMAGES: 'researchmind_phonon_images',
  CURRENT_STRUCTURE: 'researchmind_current_structure',
  SESSION_ID: 'researchmind_session_id',
} as const

export class StorageService {
  /**
   * Save chat history
   */
  static saveChatHistory(messages: Message[]): void {
    try {
      localStorage.setItem(STORAGE_KEYS.CHAT_HISTORY, JSON.stringify(messages))
    } catch (error) {
      console.error('Failed to save chat history:', error)
    }
  }

  /**
   * Load chat history
   */
  static loadChatHistory(): Message[] {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.CHAT_HISTORY)
      return data ? JSON.parse(data) : []
    } catch (error) {
      console.error('Failed to load chat history:', error)
      return []
    }
  }

  /**
   * Save structures
   */
  static saveStructures(structures: CrystalStructure[]): void {
    try {
      localStorage.setItem(STORAGE_KEYS.STRUCTURES, JSON.stringify(structures))
    } catch (error) {
      console.error('Failed to save structures:', error)
    }
  }

  /**
   * Load structures
   */
  static loadStructures(): CrystalStructure[] {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.STRUCTURES)
      return data ? JSON.parse(data) : []
    } catch (error) {
      console.error('Failed to load structures:', error)
      return []
    }
  }

  /**
   * Save current structure
   */
  static saveCurrentStructure(structure: CrystalStructure | null): void {
    try {
      if (structure) {
        localStorage.setItem(STORAGE_KEYS.CURRENT_STRUCTURE, JSON.stringify(structure))
      } else {
        localStorage.removeItem(STORAGE_KEYS.CURRENT_STRUCTURE)
      }
    } catch (error) {
      console.error('Failed to save current structure:', error)
    }
  }

  /**
   * Load current structure
   */
  static loadCurrentStructure(): CrystalStructure | null {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.CURRENT_STRUCTURE)
      return data ? JSON.parse(data) : null
    } catch (error) {
      console.error('Failed to load current structure:', error)
      return null
    }
  }

  /**
   * Save phonon images
   */
  static savePhononImages(images: PhononImage[]): void {
    try {
      localStorage.setItem(STORAGE_KEYS.PHONON_IMAGES, JSON.stringify(images))
    } catch (error) {
      console.error('Failed to save phonon images:', error)
    }
  }

  /**
   * Load phonon images
   */
  static loadPhononImages(): PhononImage[] {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.PHONON_IMAGES)
      return data ? JSON.parse(data) : []
    } catch (error) {
      console.error('Failed to load phonon images:', error)
      return []
    }
  }

  /**
   * Save session ID
   */
  static saveSessionId(sessionId: string): void {
    try {
      localStorage.setItem(STORAGE_KEYS.SESSION_ID, sessionId)
    } catch (error) {
      console.error('Failed to save session ID:', error)
    }
  }

  /**
   * Load session ID
   */
  static loadSessionId(): string | null {
    try {
      return localStorage.getItem(STORAGE_KEYS.SESSION_ID)
    } catch (error) {
      console.error('Failed to load session ID:', error)
      return null
    }
  }

  /**
   * Clear all stored data
   */
  static clearAll(): void {
    try {
      Object.values(STORAGE_KEYS).forEach(key => {
        localStorage.removeItem(key)
      })
    } catch (error) {
      console.error('Failed to clear storage:', error)
    }
  }

  /**
   * Clear chat history only
   */
  static clearChatHistory(): void {
    try {
      localStorage.removeItem(STORAGE_KEYS.CHAT_HISTORY)
    } catch (error) {
      console.error('Failed to clear chat history:', error)
    }
  }

  /**
   * Clear structures only
   */
  static clearStructures(): void {
    try {
      localStorage.removeItem(STORAGE_KEYS.STRUCTURES)
      localStorage.removeItem(STORAGE_KEYS.CURRENT_STRUCTURE)
    } catch (error) {
      console.error('Failed to clear structures:', error)
    }
  }

  /**
   * Clear phonon images only
   */
  static clearPhononImages(): void {
    try {
      localStorage.removeItem(STORAGE_KEYS.PHONON_IMAGES)
    } catch (error) {
      console.error('Failed to clear phonon images:', error)
    }
  }

  /**
   * Get storage size in bytes
   */
  static getStorageSize(): number {
    try {
      let total = 0
      Object.values(STORAGE_KEYS).forEach(key => {
        const item = localStorage.getItem(key)
        if (item) {
          total += item.length * 2 // UTF-16 encoding
        }
      })
      return total
    } catch (error) {
      console.error('Failed to get storage size:', error)
      return 0
    }
  }

  /**
   * Get storage size in human-readable format
   */
  static getStorageSizeFormatted(): string {
    const bytes = this.getStorageSize()
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  }
}

