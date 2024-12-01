{{/*
Expand the name of the chart.
*/}}
{{- define "ziti-edge-proxy.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "ziti-edge-proxy.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "ziti-edge-proxy.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "ziti-edge-proxy.labels" -}}
helm.sh/chart: {{ include "ziti-edge-proxy.chart" . }}
{{ include "ziti-edge-proxy.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "ziti-edge-proxy.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ziti-edge-proxy.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "ziti-edge-proxy.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "ziti-edge-proxy.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}


{{/*
Create the name of the identity secret
*/}}
{{- define "ziti-edge-proxy.secret.identitySecretName" -}}
{{- if .Values.appConfig.identity.existingSecret }}
{{- .Values.appConfig.identity.existingSecret }}
{{- else }}
{{- default (printf "%s-identity" (include "ziti-edge-proxy.fullname" . )) }}
{{- end }}
{{- end }}

{{/*
Create the name of the credential secret
*/}}
{{- define "ziti-edge-proxy.secret.credentialSecretName" -}}
{{- if .Values.appConfig.credential.existingSecret }}
{{- .Values.appConfig.credential.existingSecret }}
{{- else }}
{{- default (printf "%s-credential" (include "ziti-edge-proxy.fullname" . )) }}
{{- end }}
{{- end }}