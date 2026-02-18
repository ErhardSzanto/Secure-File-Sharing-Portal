import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ApiService } from './services/api.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
  email = 'user@portal.local';
  password = 'User123!';

  token = '';
  me: any = null;
  errorMessage = '';

  activeTab: 'my' | 'shared' | 'activity' | 'admin' = 'my';

  myFiles: any[] = [];
  sharedFiles: any[] = [];
  recentActivity: any[] = [];

  selectedFile: any = null;
  selectedFileAudit: any[] = [];
  shareEmail = '';
  linkExpiry = '';
  linkJustification = '';

  adminFiles: any[] = [];
  adminAudit: any[] = [];
  policyRules: any[] = [];
  overrideFileId: number | null = null;
  overrideLabel = 'Internal';
  overrideJustification = '';

  uploadDragOver = false;
  uploadStatus = '';
  lastUploadResult: any = null;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    const stored = localStorage.getItem('portal_token');
    if (stored) {
      this.token = stored;
      this.bootstrapSession();
    }
  }

  login(): void {
    this.errorMessage = '';
    this.api.login(this.email, this.password).subscribe({
      next: (tokenData) => {
        this.token = tokenData.access_token;
        localStorage.setItem('portal_token', this.token);
        this.bootstrapSession();
      },
      error: (err) => {
        if (err?.status === 0) {
          this.errorMessage = 'Cannot reach backend (http://localhost:8000) or blocked by CORS. Verify backend is running and frontend URL is localhost/127.0.0.1.';
          return;
        }
        this.errorMessage = err?.error?.detail || 'Login failed';
      }
    });
  }

  logout(): void {
    this.token = '';
    this.me = null;
    this.selectedFile = null;
    this.selectedFileAudit = [];
    localStorage.removeItem('portal_token');
  }

  bootstrapSession(): void {
    this.api.me(this.token).subscribe({
      next: (user) => {
        this.me = user;
        this.loadTabs();
        if (this.me.role === 'Admin') {
          this.loadAdminPanel();
        }
      },
      error: () => {
        this.logout();
        this.errorMessage = 'Session invalid or backend unavailable. Please login again.';
      }
    });
  }

  loadTabs(): void {
    this.api.listFiles(this.token, 'mine').subscribe((rows) => {
      this.myFiles = rows;
    });

    this.api.listFiles(this.token, 'shared').subscribe((rows) => {
      this.sharedFiles = rows;
    });

    this.api.recentActivity(this.token).subscribe((rows) => {
      this.recentActivity = rows;
    });
  }

  loadAdminPanel(): void {
    if (this.me?.role !== 'Admin') {
      return;
    }

    this.api.adminFiles(this.token).subscribe((rows) => {
      this.adminFiles = rows;
    });

    this.api.adminAudit(this.token).subscribe((rows) => {
      this.adminAudit = rows;
    });

    this.api.adminPolicy(this.token).subscribe((result) => {
      this.policyRules = result.rules;
    });
  }

  setTab(tab: 'my' | 'shared' | 'activity' | 'admin'): void {
    this.activeTab = tab;
    if (tab === 'admin') {
      this.loadAdminPanel();
    }
  }

  selectFile(fileId: number): void {
    this.selectedFile = null;
    this.selectedFileAudit = [];

    this.api.fileDetails(this.token, fileId).subscribe((details) => {
      this.selectedFile = details;
      this.api.fileAudit(this.token, fileId).subscribe((auditRows) => {
        this.selectedFileAudit = auditRows;
      });
    });
  }

  onFileInputChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.uploadFile(input.files[0]);
    }
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    this.uploadDragOver = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    this.uploadDragOver = false;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    this.uploadDragOver = false;

    const file = event.dataTransfer?.files?.[0];
    if (file) {
      this.uploadFile(file);
    }
  }

  uploadFile(file: File): void {
    this.uploadStatus = 'Uploading and scanning...';
    this.lastUploadResult = null;
    this.api.upload(this.token, file).subscribe({
      next: (result) => {
        this.lastUploadResult = result;
        this.uploadStatus = `Uploaded: ${result.filename} (${result.label}, ${result.policy_decision})`;
        this.loadTabs();
      },
      error: (err) => {
        this.uploadStatus = err?.error?.detail || 'Upload failed';
      }
    });
  }

  addInternalShare(): void {
    if (!this.selectedFile || !this.shareEmail.trim()) {
      return;
    }

    this.api.addInternalShare(this.token, this.selectedFile.id, this.shareEmail.trim()).subscribe({
      next: () => {
        this.shareEmail = '';
        this.selectFile(this.selectedFile.id);
        this.loadTabs();
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail || 'Could not add internal share';
      }
    });
  }

  createExternalLink(): void {
    if (!this.selectedFile || !this.linkExpiry) {
      return;
    }

    this.api.createExternalLink(this.token, this.selectedFile.id, this.linkExpiry, this.linkJustification).subscribe({
      next: () => {
        this.linkJustification = '';
        this.selectFile(this.selectedFile.id);
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail || 'Could not create external link';
      }
    });
  }

  runLabelOverride(): void {
    if (this.overrideFileId === null || !this.overrideJustification.trim()) {
      return;
    }

    this.api.overrideLabel(this.token, this.overrideFileId, this.overrideLabel, this.overrideJustification).subscribe({
      next: () => {
        this.overrideJustification = '';
        this.overrideFileId = null;
        this.loadTabs();
        this.loadAdminPanel();
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail || 'Label override failed';
      }
    });
  }

  labelClass(label: string): string {
    const norm = (label || '').toLowerCase();
    if (norm.includes('highly')) {
      return 'label-high';
    }
    if (norm.includes('confidential')) {
      return 'label-conf';
    }
    if (norm.includes('public')) {
      return 'label-public';
    }
    return 'label-internal';
  }

  formatJson(value: unknown): string {
    return JSON.stringify(value, null, 2);
  }
}
