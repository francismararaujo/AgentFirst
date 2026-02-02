# Multi-Tenant Testing Guide

## 🎯 Sistema 100% Pronto!

**3 Commits Deployados:**
- `f105e34` - Merchants table + Repository
- `a8aab0c` - Centralized credentials architecture  
- `37725d9` - JWT auth + CRUD API endpoints

---

## 🧪 Como Testar

### **1. Migrar Merchant Atual**
```bash
python scripts/migrate_merchant.py --email SEU_EMAIL@exemplo.com
```

### **2. Verificar Polling**
```bash
aws logs tail /ecs/agentfirst-polling-production --follow --region us-east-1
```
Deve mostrar: `📊 Polling 1 active merchant(s)...`

### **3. Gerar JWT Token**
```python
from app.auth.jwt_auth import create_access_token
token = create_access_token("SEU_EMAIL@exemplo.com")
print(token)
```

### **4. Testar API**
```bash
# Listar merchants
curl -H "Authorization: Bearer $TOKEN" \
  https://api.agentfirst.com.br/api/merchants

# Adicionar merchant
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"merchant_id":"NOVO_ID"}' \
  https://api.agentfirst.com.br/api/merchants

# Ver status
curl -H "Authorization: Bearer $TOKEN" \
  https://api.agentfirst.com.br/api/merchants/MERCHANT_ID/status
```

---

## 📊 Endpoints Disponíveis

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/api/merchants` | Criar merchant |
| `GET` | `/api/merchants` | Listar merchants |
| `GET` | `/api/merchants/{id}` | Detalhes |
| `PUT` | `/api/merchants/{id}` | Atualizar |
| `DELETE` | `/api/merchants/{id}` | Desativar |
| `POST` | `/api/merchants/validate` | Validar ID |
| `GET` | `/api/merchants/{id}/status` | Status polling |

**Todos requerem:** `Authorization: Bearer <JWT>`

---

## 🔐 Segurança

- ✅ JWT obrigatório
- ✅ Isolamento por user_email
- ✅ Credenciais centralizadas
- ✅ Erros não revelam dados de outros usuários

---

## ✅ Checklist de Sucesso

- [ ] Merchant migrado para DynamoDB
- [ ] Polling funcionando (logs ECS)
- [ ] API retorna merchants
- [ ] Segundo merchant adicionado
- [ ] Polling com 2 merchants
- [ ] Loja aberta no iFood portal
