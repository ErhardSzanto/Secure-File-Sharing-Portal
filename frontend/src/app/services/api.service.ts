import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly baseUrl = 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  private authHeaders(token: string): HttpHeaders {
    return new HttpHeaders({ Authorization: `Bearer ${token}` });
  }

  login(email: string, password: string) {
    return this.http.post<{ access_token: string; token_type: string }>(`${this.baseUrl}/auth/login`, {
      email,
      password
    });
  }

  me(token: string) {
    return this.http.get<any>(`${this.baseUrl}/auth/me`, { headers: this.authHeaders(token) });
  }

  upload(token: string, file: File) {
    const body = new FormData();
    body.append('file', file);
    return this.http.post<any>(`${this.baseUrl}/files/upload`, body, { headers: this.authHeaders(token) });
  }

  listFiles(token: string, scope: 'mine' | 'shared' | 'all') {
    const params = new HttpParams().set('scope', scope);
    return this.http.get<any[]>(`${this.baseUrl}/files`, {
      headers: this.authHeaders(token),
      params
    });
  }

  fileDetails(token: string, id: number) {
    return this.http.get<any>(`${this.baseUrl}/files/${id}`, { headers: this.authHeaders(token) });
  }

  fileAudit(token: string, id: number) {
    return this.http.get<any[]>(`${this.baseUrl}/files/${id}/audit`, { headers: this.authHeaders(token) });
  }

  recentActivity(token: string) {
    return this.http.get<any[]>(`${this.baseUrl}/files/activity`, { headers: this.authHeaders(token) });
  }

  addInternalShare(token: string, fileId: number, email: string) {
    return this.http.post<any>(`${this.baseUrl}/files/${fileId}/share/internal`, { email }, {
      headers: this.authHeaders(token)
    });
  }

  createExternalLink(token: string, fileId: number, expiresAt: string, justification?: string) {
    return this.http.post<any>(`${this.baseUrl}/files/${fileId}/share/external-link`, {
      expires_at: expiresAt,
      justification: justification || null
    }, {
      headers: this.authHeaders(token)
    });
  }

  adminFiles(token: string) {
    return this.http.get<any[]>(`${this.baseUrl}/admin/files`, { headers: this.authHeaders(token) });
  }

  adminAudit(token: string) {
    return this.http.get<any[]>(`${this.baseUrl}/admin/audit`, { headers: this.authHeaders(token) });
  }

  adminPolicy(token: string) {
    return this.http.get<{ rules: any[] }>(`${this.baseUrl}/admin/policy`, { headers: this.authHeaders(token) });
  }

  overrideLabel(token: string, fileId: number, label: string, justification: string) {
    return this.http.post<any>(`${this.baseUrl}/admin/files/${fileId}/label-override`, {
      label,
      justification
    }, {
      headers: this.authHeaders(token)
    });
  }
}
