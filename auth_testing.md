# Dynasty 8 - Auth Testing Playbook

The app uses Emergent-managed Google Auth. Testing agents must create a session record directly in MongoDB and pass `Authorization: Bearer <session_token>` header, since Google OAuth cannot be automated.

## Step 1: Create test admin user + session
```
mongosh --eval "
use('test_database');
var adminUserId = 'user_test_admin01';
var adminToken = 'test_session_admin_' + Date.now();
db.users.updateOne({user_id: adminUserId},
  {\$set: {user_id: adminUserId, email: 'admin@dynasty8.no', name: 'Dynasty Admin', role: 'admin', employee_number: 'A001', picture: null, created_at: new Date().toISOString()}},
  {upsert: true});
db.user_sessions.insertOne({user_id: adminUserId, session_token: adminToken, expires_at: new Date(Date.now() + 7*24*60*60*1000).toISOString(), created_at: new Date().toISOString()});

var ansattUserId = 'user_test_ansatt01';
var ansattToken = 'test_session_ansatt_' + Date.now();
db.users.updateOne({user_id: ansattUserId},
  {\$set: {user_id: ansattUserId, email: 'sara@dynasty8.no', name: 'Sara Hansen', role: 'ansatt', employee_number: 'E101', picture: null, created_at: new Date().toISOString()}},
  {upsert: true});
db.user_sessions.insertOne({user_id: ansattUserId, session_token: ansattToken, expires_at: new Date(Date.now() + 7*24*60*60*1000).toISOString(), created_at: new Date().toISOString()});

print('ADMIN_TOKEN=' + adminToken);
print('ANSATT_TOKEN=' + ansattToken);
"
```

## Step 2: Backend API tests via curl
```
API=https://dynasty-crm-2.preview.emergentagent.com/api

# auth/me
curl -s "$API/auth/me" -H "Authorization: Bearer $ADMIN_TOKEN"

# price-matrix (no auth needed)
curl -s "$API/price-matrix"

# price-calculator
curl -s -X POST "$API/price-calculator" -H "Content-Type: application/json" \
  -d '{"zone":"Oslo Sentrum","package":"MLO","addons":["garasje","hage"],"tenant_count":2,"discount_type":"10"}'

# create a sale as ansatt
curl -s -X POST "$API/sales" -H "Content-Type: application/json" -H "Authorization: Bearer $ANSATT_TOKEN" \
  -d '{"customer_name":"Ola Test","phone":"+47 900 12 345","address":"Karl Johans gate 1","zone":"Oslo Sentrum","package":"MLO","addons":["garasje"],"tenant_count":0,"discount_type":"5","sale_date":"2026-02-15","comment":"test","status":"aktiv"}'

# list sales (admin)
curl -s "$API/sales" -H "Authorization: Bearer $ADMIN_TOKEN"

# stats
curl -s "$API/stats/dashboard" -H "Authorization: Bearer $ANSATT_TOKEN"
curl -s "$API/stats/admin" -H "Authorization: Bearer $ADMIN_TOKEN"

# export
curl -s "$API/export/csv" -H "Authorization: Bearer $ADMIN_TOKEN" -o /tmp/dynasty.csv
curl -s "$API/export/xlsx" -H "Authorization: Bearer $ADMIN_TOKEN" -o /tmp/dynasty.xlsx
```

## Step 3: Browser testing
Set session_token cookie before navigating:
```
await page.context.add_cookies([{
  "name": "session_token", "value": ADMIN_TOKEN,
  "domain": "dynasty-crm-2.preview.emergentagent.com",
  "path": "/", "httpOnly": True, "secure": True, "sameSite": "None"
}]);
await page.goto("https://dynasty-crm-2.preview.emergentagent.com/dashboard");
```

## Cleanup
```
mongosh --eval "
use('test_database');
db.users.deleteMany({email: {\$in: ['admin@dynasty8.no','sara@dynasty8.no']}});
db.user_sessions.deleteMany({session_token: /test_session_/});
db.sales.deleteMany({customer_name: 'Ola Test'});
"
```

## Expected price for the calculator test above
- Base: Oslo Sentrum MLO = 26 000
- +Garasje 10% = +2600
- +Hage 5% = +1300
- +Leietakere 2 × 500 = +1000
- Subtotal = 30 900
- -Rabatt 10% = 27 810
