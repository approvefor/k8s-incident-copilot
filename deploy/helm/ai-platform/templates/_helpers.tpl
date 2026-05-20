{{- define "ai-platform.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "ai-platform.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name (include "ai-platform.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "ai-platform.labels" -}}
app.kubernetes.io/name: {{ include "ai-platform.name" . }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "ai-platform.apiUrl" -}}
{{- printf "http://%s-api:%v" (include "ai-platform.fullname" .) .Values.api.port -}}
{{- end -}}

{{- define "ai-platform.image" -}}
{{- $registry := .registry -}}
{{- $repository := .image.repository -}}
{{- if .image.digest -}}
{{- printf "%s/%s@%s" $registry $repository .image.digest -}}
{{- else -}}
{{- printf "%s/%s:%s" $registry $repository .image.tag -}}
{{- end -}}
{{- end -}}

{{- define "ai-platform.qdrantUrl" -}}
{{- printf "http://%s-qdrant:6333" .Release.Name -}}
{{- end -}}

{{- define "ai-platform.postgresqlHost" -}}
{{- printf "%s-postgresql" .Release.Name -}}
{{- end -}}

{{- define "ai-platform.databaseUrl" -}}
{{- if not .Values.postgresql.enabled -}}
{{- fail "postgresql.enabled=false requires api.audit.existingSecret with a database-url key" -}}
{{- end -}}
{{- printf "postgresql+psycopg://%s:%s@%s:5432/%s" .Values.postgresql.auth.username .Values.postgresql.auth.password (include "ai-platform.postgresqlHost" .) .Values.postgresql.auth.database -}}
{{- end -}}
