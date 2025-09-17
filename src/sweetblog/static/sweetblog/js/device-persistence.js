(function() {
    'use strict';

    console.log('[DevicePersistence] Initializing device UUID persistence script');

    const DEVICE_KEY = 'device_uuid';
    const STORAGE_KEYS = {
        localStorage: 'sb_device_uuid',
        sessionStorage: 'sb_temp_device_uuid',
        indexedDB: 'sb_persistent_device_uuid',
        cookie: 'sb_fallback_device_uuid'
    };

    // Add reload prevention mechanism
    const RELOAD_PREVENTION_KEY = 'sb_reload_timestamp';
    const RELOAD_COOLDOWN = 5000; // 5 seconds cooldown

    console.log('[DevicePersistence] Storage keys configured:', STORAGE_KEYS);

    // Helper to check if we recently reloaded
    function hasRecentlyReloaded() {
        const lastReload = sessionStorage.getItem(RELOAD_PREVENTION_KEY);
        if (!lastReload) return false;

        const timeDiff = Date.now() - parseInt(lastReload);
        return timeDiff < RELOAD_COOLDOWN;
    }

    // Helper to mark that we're about to reload
    function markReloadAttempt() {
        sessionStorage.setItem(RELOAD_PREVENTION_KEY, Date.now().toString());
    }

    // Helper to get device UUID from cookies
    function getDeviceUuidFromCookie() {
        console.log('[DevicePersistence] Getting device UUID from cookies');
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === DEVICE_KEY) {
                console.log('[DevicePersistence] Found device UUID in cookie:', value);
                return value;
            }
        }
        console.log('[DevicePersistence] No device UUID found in cookies');
        return null;
    }

    // Helper to set cookie with extended expiration
    function setCookie(name, value, days = 365) {
        console.log(`[DevicePersistence] Setting cookie: ${name} = ${value} for ${days} days`);
        const date = new Date();
        date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
        const expires = "expires=" + date.toUTCString();
        document.cookie = `${name}=${value};${expires};path=/;SameSite=Lax`;
        console.log('[DevicePersistence] Cookie set successfully');
    }

    // Helper to get cookie value
    function getCookie(name) {
        console.log(`[DevicePersistence] Getting cookie: ${name}`);
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [cookieName, cookieValue] = cookie.trim().split('=');
            if (cookieName === name) {
                console.log(`[DevicePersistence] Found cookie ${name}: ${cookieValue}`);
                return cookieValue;
            }
        }
        console.log(`[DevicePersistence] Cookie ${name} not found`);
        return null;
    }

    // IndexedDB operations (reusing pattern from persistent-session.js)
    const IndexedDBStorage = {
        dbName: 'SweetBlogDB',
        storeName: 'devices',

        async init() {
            console.log('[DevicePersistence] Initializing IndexedDB');
            return new Promise((resolve, reject) => {
                const request = indexedDB.open(this.dbName, 2); // Increment version

                request.onerror = () => {
                    console.error('[DevicePersistence] IndexedDB init error:', request.error);
                    reject(request.error);
                };
                request.onsuccess = () => {
                    console.log('[DevicePersistence] IndexedDB initialized successfully');
                    resolve(request.result);
                };

                request.onupgradeneeded = (event) => {
                    console.log('[DevicePersistence] IndexedDB upgrade needed');
                    const db = event.target.result;
                    if (!db.objectStoreNames.contains(this.storeName)) {
                        db.createObjectStore(this.storeName, { keyPath: 'key' });
                        console.log('[DevicePersistence] Created object store:', this.storeName);
                    }
                };
            });
        },

        async set(key, value) {
            console.log(`[DevicePersistence] IndexedDB set: ${key} = ${value}`);
            try {
                const db = await this.init();
                const transaction = db.transaction([this.storeName], 'readwrite');
                const store = transaction.objectStore(this.storeName);
                store.put({ key, value, timestamp: Date.now() });
                console.log('[DevicePersistence] IndexedDB set successful');
            } catch (e) {
                console.error('[DevicePersistence] IndexedDB set error:', e);
            }
        },

        async get(key) {
            console.log(`[DevicePersistence] IndexedDB get: ${key}`);
            try {
                const db = await this.init();
                const transaction = db.transaction([this.storeName], 'readonly');
                const store = transaction.objectStore(this.storeName);
                const request = store.get(key);

                return new Promise((resolve) => {
                    request.onsuccess = () => {
                        const result = request.result;
                        const value = result ? result.value : null;
                        console.log(`[DevicePersistence] IndexedDB get result: ${value}`);
                        resolve(value);
                    };
                    request.onerror = () => {
                        console.error('[DevicePersistence] IndexedDB get request error');
                        resolve(null);
                    };
                });
            } catch (e) {
                console.error('[DevicePersistence] IndexedDB get error:', e);
                return null;
            }
        }
    };

    // Web Storage with obfuscation (reusing pattern from persistent-session.js)
    const ObfuscatedStorage = {
        encode(value) {
            return btoa(encodeURIComponent(value));
        },

        decode(value) {
            try {
                return decodeURIComponent(atob(value));
            } catch {
                return null;
            }
        },

        set(storage, key, value) {
            const storageName = storage === localStorage ? 'localStorage' : 'sessionStorage';
            console.log(`[DevicePersistence] ${storageName} set: ${key} = ${value}`);
            try {
                storage.setItem(key, this.encode(value));
                // Also store with timestamp
                storage.setItem(key + '_ts', Date.now().toString());
                console.log(`[DevicePersistence] ${storageName} set successful`);
            } catch (e) {
                console.error(`[DevicePersistence] ${storageName} set error:`, e);
            }
        },

        get(storage, key) {
            const storageName = storage === localStorage ? 'localStorage' : 'sessionStorage';
            console.log(`[DevicePersistence] ${storageName} get: ${key}`);
            try {
                const encoded = storage.getItem(key);
                const decoded = encoded ? this.decode(encoded) : null;
                console.log(`[DevicePersistence] ${storageName} get result: ${decoded}`);
                return decoded;
            } catch (e) {
                console.error(`[DevicePersistence] ${storageName} get error:`, e);
                return null;
            }
        }
    };

    // Main device UUID persistence manager
    const DevicePersistence = {
        async saveDeviceUuid(deviceUuid) {
            if (!deviceUuid) {
                console.log('[DevicePersistence] No device UUID to save');
                return;
            }

            console.log(`[DevicePersistence] Saving device UUID to all storage locations: ${deviceUuid}`);

            // Save to multiple locations
            // 1. LocalStorage
            ObfuscatedStorage.set(localStorage, STORAGE_KEYS.localStorage, deviceUuid);

            // 2. SessionStorage
            ObfuscatedStorage.set(sessionStorage, STORAGE_KEYS.sessionStorage, deviceUuid);

            // 3. IndexedDB
            await IndexedDBStorage.set(STORAGE_KEYS.indexedDB, deviceUuid);

            // 4. Additional cookie
            setCookie(STORAGE_KEYS.cookie, deviceUuid);

            // 5. Window.name (survives page refresh)
            try {
                const windowData = JSON.parse(window.name || '{}');
                windowData.sb_device_uuid = deviceUuid;
                window.name = JSON.stringify(windowData);
                console.log('[DevicePersistence] Saved to window.name');
            } catch (e) {
                window.name = JSON.stringify({ sb_device_uuid: deviceUuid });
                console.log('[DevicePersistence] Created new window.name with device UUID');
            }

            console.log('[DevicePersistence] Device UUID saved to all locations');
        },

        async getStoredDeviceUuidFromNonCookieStorage() {
            console.log('[DevicePersistence] Attempting to retrieve stored device UUID from non-cookie sources');
            let deviceUuid = null;

            // Check localStorage
            deviceUuid = ObfuscatedStorage.get(localStorage, STORAGE_KEYS.localStorage);
            if (deviceUuid) {
                console.log('[DevicePersistence] Found device UUID in localStorage');
                return deviceUuid;
            }

            // Check sessionStorage
            deviceUuid = ObfuscatedStorage.get(sessionStorage, STORAGE_KEYS.sessionStorage);
            if (deviceUuid) {
                console.log('[DevicePersistence] Found device UUID in sessionStorage');
                return deviceUuid;
            }

            // Check IndexedDB
            deviceUuid = await IndexedDBStorage.get(STORAGE_KEYS.indexedDB);
            if (deviceUuid) {
                console.log('[DevicePersistence] Found device UUID in IndexedDB');
                return deviceUuid;
            }

            // Check window.name
            try {
                const data = JSON.parse(window.name);
                if (data && data.sb_device_uuid) {
                    console.log('[DevicePersistence] Found device UUID in window.name');
                    return data.sb_device_uuid;
                }
            } catch (e) {
                console.log('[DevicePersistence] Could not parse window.name');
            }

            console.log('[DevicePersistence] No stored device UUID found in non-cookie storage');
            return null;
        },

        async restoreDeviceUuid() {
            console.log('[DevicePersistence] Starting device UUID restoration process');

            // Check if we recently reloaded to prevent infinite loops
            if (hasRecentlyReloaded()) {
                console.log('[DevicePersistence] Recently reloaded, skipping reload to prevent infinite loop');
                return;
            }

            // First check storages (excluding cookies) for device UUID
            const storedDeviceUuid = await this.getStoredDeviceUuidFromNonCookieStorage();
            const currentDeviceUuid = getDeviceUuidFromCookie();

            if (storedDeviceUuid && currentDeviceUuid && storedDeviceUuid !== currentDeviceUuid) {
                console.log('[DevicePersistence] Found different device UUID in storage, overriding cookie and reloading');
                // Mark reload attempt and override the cookie with stored value
                markReloadAttempt();
                setCookie(DEVICE_KEY, storedDeviceUuid, 365);
                // Reload the page to ensure correct device UUID is used
                window.location.reload();
                return;
            } else if (storedDeviceUuid && !currentDeviceUuid) {
                console.log('[DevicePersistence] Found device UUID in storage, setting cookie and reloading');
                // Mark reload attempt, set the cookie and reload
                markReloadAttempt();
                setCookie(DEVICE_KEY, storedDeviceUuid, 365);
                window.location.reload();
                return;
            }

            // If we get here, either:
            // 1. No stored device UUID exists, or
            // 2. Stored and current device UUIDs match, or
            // 3. Only current device UUID exists

            if (currentDeviceUuid) {
                console.log('[DevicePersistence] Device UUID found in cookie, saving to storage');
                await this.saveDeviceUuid(currentDeviceUuid);
            } else {
                console.log('[DevicePersistence] No device UUID found in cookie or storage');
            }
        },

        async init() {
            console.log('[DevicePersistence] Initializing device UUID persistence manager');

            // Initial restoration
            await this.restoreDeviceUuid();

            // Listen for storage events from other tabs
            console.log('[DevicePersistence] Setting up storage event listener for cross-tab sync');
            window.addEventListener('storage', async (e) => {
                console.log('[DevicePersistence] Storage event detected:', e.key);
                if (e.key === STORAGE_KEYS.localStorage) {
                    const deviceUuid = ObfuscatedStorage.decode(e.newValue);
                    if (deviceUuid && deviceUuid !== getDeviceUuidFromCookie()) {
                        console.log('[DevicePersistence] Syncing device UUID from another tab');
                        setCookie(DEVICE_KEY, deviceUuid, 365);
                    }
                }
            });

            console.log('[DevicePersistence] Initialization complete');
        }
    };

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        console.log('[DevicePersistence] DOM is loading, waiting for DOMContentLoaded');
        document.addEventListener('DOMContentLoaded', () => {
            console.log('[DevicePersistence] DOMContentLoaded fired, initializing');
            DevicePersistence.init();
        });
    } else {
        console.log('[DevicePersistence] DOM already loaded, initializing immediately');
        DevicePersistence.init();
    }
})();