const api = {
    async request(method, url, data = null) {
        const options = {
            method,
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin'
        };
        if (method !== 'GET') {
            options.body = data !== null && data !== undefined ? JSON.stringify(data) : JSON.stringify({});
        }
        try {
            const res = await fetch(url, options);
            const json = await res.json();
            if (res.status === 401 && !url.includes('/auth/login')) {
                window.location.href = '/login';
                return json;
            }
            return json;
        } catch (err) {
            console.error('API Error:', err);
            return { success: false, error: { code: 'NETWORK_ERROR', message: 'Connection failed' } };
        }
    },
    get(url) { return this.request('GET', url); },
    post(url, data) { return this.request('POST', url, data); },
    put(url, data) { return this.request('PUT', url, data); },
    patch(url, data) { return this.request('PATCH', url, data); },
    delete(url) { return this.request('DELETE', url); },
    async upload(url, formData) {
        try {
            const res = await fetch(url, { method: 'POST', credentials: 'same-origin', body: formData });
            const json = await res.json();
            if (res.status === 401) { window.location.href = '/login'; return json; }
            return json;
        } catch (err) {
            console.error('Upload Error:', err);
            return { success: false, error: { code: 'NETWORK_ERROR', message: 'Upload failed' } };
        }
    }
};
