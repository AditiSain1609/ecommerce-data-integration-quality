"""Generate deterministic, relational sample data with intentional quality defects."""
import random
from pathlib import Path
import pandas as pd
import numpy as np

OUT = Path(__file__).resolve().parents[1] / "sample_data"

def main():
    random.seed(41); np.random.seed(41); OUT.mkdir(exist_ok=True)
    customers = pd.DataFrame([{"customer_id":f"C{i:04}","customer_name":f"Customer {i}","email":f"customer{i}@example.com","phone":f"555-{i:07}","city":random.choice(["Austin","Seattle","Boston","Chicago"]),"state":random.choice(["TX","WA","MA","IL"]),"country":"US"} for i in range(1,501)])
    customers.loc[5,"email"] = None; customers.loc[8,"email"] = "bad-email"; customers.loc[12,"customer_name"] += "  "; customers = pd.concat([customers, customers.iloc[[0]]], ignore_index=True)
    products = pd.DataFrame([{"product_id":f"P{i:03}","product_name":f"Product {i}","category":random.choice(["Home","Electronics","Apparel","Beauty"]),"price":round(random.uniform(5,500),2),"stock_quantity":random.randint(0,100)} for i in range(1,101)])
    products.loc[3,"category"] = None; products.loc[4,"price"] = -12; products.loc[6,"category"] = " eLeCtRoNiCs "
    orders=[]; items=[]; payments=[]
    for i in range(1,1001):
        cid=f"C{random.randint(1,500):04}" if i != 44 else "C9999"
        dt=pd.Timestamp("2025-01-01")+pd.Timedelta(days=random.randint(0,650))
        status=random.choice(["pending","processing","shipped","delivered","cancelled"])
        n=random.randint(1,3); chosen=random.sample(range(1,101),n); total=0
        for j,p in enumerate(chosen):
            q=random.randint(1,4) if i != 27 else -2; price=float(products.loc[p-1,"price"]); amount=q*price; total+=amount
            items.append({"order_item_id":f"OI{i:04}-{j+1}","order_id":f"O{i:05}","product_id":f"P{p:03}","quantity":q,"unit_price":price})
        if i == 55: status="nonsense"
        orders.append({"order_id":f"O{i:05}","customer_id":cid,"order_date":dt.isoformat(),"order_status":status,"total_amount":round(total,2),"source_system":random.choice(["web","mobile","marketplace"])})
        payments.append({"payment_id":f"PAY{i:05}","order_id":f"O{i:05}" if i != 63 else "O99999","payment_method":random.choice(["card","paypal","gift_card"]),"payment_status":"paid","payment_amount":round(total,2),"transaction_date":dt.isoformat(),"source_system":"payments_api"})
    orders=pd.DataFrame(orders); orders.loc[1,"order_id"]=orders.loc[0,"order_id"]; orders.loc[2,"order_date"]="not-a-date"
    payments=pd.DataFrame(payments); payments=pd.concat([payments,payments.iloc[[0]]],ignore_index=True)
    for name, df in [("customers",customers),("products",products),("orders",orders),("order_items",pd.DataFrame(items)),("payments",payments)]: df.to_csv(OUT/f"{name}.csv",index=False)
    print(f"Generated deterministic sample files in {OUT}")

if __name__ == "__main__": main()
