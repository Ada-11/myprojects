# Structured Queries and Outputs Reference

## 1. Simple Filter: What's the deductible on the Gold PPO plan?

### SQL Query
```sql
SELECT annual_deductible 
FROM plans 
WHERE LOWER(plan_name) = 'gold ppo';
```

### Output Table
|   annual_deductible |
|--------------------:|
|                2000 |

---

## 2. Aggregation: How many claims are pending for member M1001?

### SQL Query
```sql
SELECT COUNT(*) AS pending_count 
FROM claims 
WHERE member_id = 'M1001' 
  AND LOWER(status) = 'pending';
```

### Output Table
|   pending_count |
|----------------:|
|               1 |

---

## 3. Numerical Comparison: Which plans have a monthly premium under $400?

### SQL Query
```sql
SELECT plan_name, monthly_premium 
FROM plans 
WHERE monthly_premium < 400 
ORDER BY monthly_premium DESC;
```

### Output Table
| plan_name   |   monthly_premium |
|:------------|------------------:|
| Silver HMO  |               300 |
| Bronze HMO  |               150 |

---

## 4. Table Relation: Relational JOIN between claims and plans

### SQL Query
```sql
SELECT 
    c.claim_id, 
    c.member_id, 
    p.plan_name, 
    c.claim_amount 
FROM claims c 
JOIN plans p ON c.plan_id = p.plan_id;
```

### Output Table
| claim_id   | member_id   | plan_name   |   claim_amount |
|:-----------|:------------|:------------|---------------:|
| C1001      | M1001       | Gold PPO    |            250 |
| C1002      | M1001       | Gold PPO    |           1200 |
| C1003      | M1002       | Silver HMO  |            150 |
| C1004      | M1002       | Silver HMO  |            900 |
| C1005      | M1003       | Bronze HMO  |             50 |

---

## 5. Top-N Analysis: Most claimed medical procedures

### SQL Query
```sql
SELECT 
    procedure, 
    COUNT(*) AS claim_count, 
    SUM(claim_amount) AS total_claimed_dollars
FROM claims 
GROUP BY procedure 
ORDER BY claim_count DESC 
LIMIT 5;
```

### Output Table
| procedure   |   claim_count |   total_claimed_dollars |
|:------------|--------------:|------------------------:|
| X-ray       |             3 |                     450 |
| Surgery     |             2 |                    2100 |

---

