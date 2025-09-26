# Infra Map Add-on

In your `dashboard/app.py`, add:
```python
tab1, tab2, tab3 = st.tabs(["Alerts","Map","Infra Map (OSINT)"])
with tab3:
    st.subheader("Palantir/Gideon Infrastructure (OSINT)")
    key = st.text_input("Shodan API Key", type="password")
    host = st.text_input("Lookup IP/Host (e.g. palantir.com)")
    if st.button("Query") and key and host:
        os.environ["SHODAN_API"] = key
        from shodan_mapper import query_shodan
        data = query_shodan(host)
        st.json(data)
```
Privacy: Calls Shodan API directly from your machine.
