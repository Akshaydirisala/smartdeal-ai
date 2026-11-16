"""SmartDeal AI v3 — user-facing Streamlit application powered by LangGraph."""
import os
from dotenv import load_dotenv
load_dotenv()
import streamlit as st
# Streamlit Community Cloud stores keys in st.secrets, not necessarily os.environ.
# Copy only known backend settings into this server process before importing tools.
for secret_name in ('SERPAPI_KEY','KEENABLE_API_KEY','SUPABASE_URL','SUPABASE_SECRET_KEY','OLLAMA_MODEL','OLLAMA_URL','CACHE_HOURS'):
    try:
        if not os.getenv(secret_name) and secret_name in st.secrets:
            os.environ[secret_name] = str(st.secrets[secret_name])
    except (FileNotFoundError, KeyError):
        pass
import pandas as pd
from agent.graph import graph
from agent.repository import get_store

st.set_page_config(page_title='SmartDeal AI | Smart purchase decisions',page_icon='🛍️',layout='wide')
st.title('🛍️ SmartDeal AI')
st.caption('Find the cheapest listing AND understand the value of warranties, returns, delivery and retailer benefits.')
with st.sidebar:
    st.header('Decision settings')
    live=bool(os.getenv('SERPAPI_KEY', '').strip())
    st.caption('Product data: Live Google Shopping')
    priority=st.selectbox('Shopping priority',['balanced','price','protection','returns'],format_func=lambda x:{'balanced':'Best overall','price':'Lowest listed price','protection':'Warranty and protection','returns':'Return flexibility'}[x])
    location=st.text_input('Shopping location','United States')
    budget=st.number_input('Maximum listed price ($, 0 = any)',min_value=0.,value=0.,step=10.)
    minimum=st.slider('Minimum review rating',0.,5.,0.,0.5)
    refresh=st.checkbox('Refresh prices (costs search credit)',False)
    keenable=st.checkbox('Research policy pages via Keenable',False,help='Optional independent web-search evidence. Does not verify listing-specific coverage.')
    ollama=st.checkbox('Ask local Qwen3 for a second explanation',False)
    st.caption('Database: Supabase' if os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_SECRET_KEY') else 'Database: local SQLite')
    st.caption('Keenable is optional. Live product offers require SERPAPI_KEY.')

if not live:
    st.error('Live search requires SERPAPI_KEY. Add it to Streamlit app Settings → Secrets, then restart the app.')

with st.form('shop'):
    q=st.text_input('What would you like to buy?','65 inch smart TV',placeholder='Enter the exact brand and model if possible')
    submitted=st.form_submit_button('Compare stores and benefits',type='primary',disabled=not live)
if submitted:
    with st.spinner('Running the LangGraph shopping workflow...'):
        state=graph.invoke({'query':q,'location':location,'mode':'live','priority':priority,'budget':budget or None,'min_rating':minimum,'refresh':refresh,'use_keenable':keenable,'use_ollama':ollama})
    st.session_state['run']=state
if 'run' in st.session_state:
    s=st.session_state['run']
    if s.get('error'):st.error(s['error'])
    else:
        if s.get('mode')=='demo':st.warning('SYNTHETIC DEMO: Products, listed prices, ratings and stores are fictional. Do not use these figures to shop.')
        else:st.info('Live shopping data: always verify checkout total, seller and product policies on the merchant website.')
        for n in s.get('notes',[]):st.caption(n)
        offers=s.get('ranked',[])
        st.metric('Offers retrieved',len(offers))
        groups=s.get('product_groups',{})
        if len(groups)>1:
            choice=st.selectbox('Compare the same product across retailers',list(groups),format_func=lambda k:f'{groups[k][0].title[:70]} • {len(groups[k])} offers')
            if choice!=s.get('selected_id'):
                from smartdeal.decision import compare_stores
                s['comparison']=compare_stores(offers,s['query'],priority=s['priority'],selected_product_id=choice)
                s['selected_id']=choice
                d=s['comparison']
                if not d.get('warning'):
                    s['explanation']=(f"Cheapest listing: {d['cheapest'].offer.merchant} ${d['cheapest'].offer.price:.2f}. "
                                      f"Best for your selected priority: {d['overall'].offer.merchant} ${d['overall'].offer.price:.2f}. "
                                      'Verify shipping, seller, membership and exact-item warranty terms before buying.')
        c=s.get('comparison',{})
        if c.get('warning'):
            st.warning(c['warning'])
        elif c:
            a,b,d=st.columns(3)
            a.metric('💲 Cheapest listing',c['cheapest'].offer.merchant,f'${c["cheapest"].offer.price:.2f}')
            b.metric('🏆 Best overall for your needs',c['overall'].offer.merchant,f'${c["overall"].offer.price:.2f}')
            d.metric('🛡️ Documented protection',c['protection'].offer.merchant if c.get('protection') else 'Not established')
        st.subheader('Decision explanation')
        st.write(s.get('explanation',''))
        if c and not c.get('warning'):
            st.subheader('Benefits by retailer')
            for d in c['rows']:
                with st.expander(f'{d.offer.merchant} • ${d.offer.price:.2f} • Decision score {d.score:.1f}/100'):
                    p=d.policy
                    st.write('**Return policy:** '+(p.returns_description if p else 'Unverified'))
                    st.write('**Warranty:** '+(p.warranty_description if p else 'Unverified'))
                    st.write('**Exceptions:** '+(p.exclusions if p else 'Verify seller-specific rules'))
                    if p:
                        for url in p.urls:st.markdown(f'[Official policy source]({url})')
                    st.caption('Category-level only; no individual listing eligibility has been verified.')
        st.subheader('Individual listings')
        data=[]
        for o in offers:
            data.append({'Title':o.title,'Retailer':o.merchant,'Price':o.price,'Shipping':o.shipping,'Rating':o.rating,'Reviews':o.reviews,'Product ID':o.product_id,'Checked':o.checked_at,'Link':o.url if s.get('mode')=='live' else 'Demo only'})
        st.dataframe(pd.DataFrame(data),hide_index=True,use_container_width=True)
        st.download_button('Export results',pd.DataFrame(data).to_csv(index=False),'smartdeal-comparison.csv','text/csv')
        if s.get('mode')=='live':
            for i,o in enumerate(offers[:10]):
                st.markdown(f'**{i+1}. {o.merchant}** — {o.title} — ${o.price:.2f} · [View listing]({o.url})')
        if s.get('web_policy_evidence'):
            with st.expander('Optional Keenable web research (not independently verified)'):
                st.json(s['web_policy_evidence'])
        with st.expander('Price history for a matching product / retailer'):
            items=[o for o in offers if o.product_id]
            if items:
                selected=st.selectbox('Offer',items,format_func=lambda x:f'{x.merchant}: {x.title[:55]}')
                try:
                    rows=get_store().history(selected.product_id,selected.merchant)
                    if rows:
                        chart=pd.DataFrame(rows,columns=['checked_at','price'])
                        chart['checked_at']=pd.to_datetime(chart['checked_at'],utc=True)
                        st.line_chart(chart.set_index('checked_at')['price'])
                    else:st.caption('No historical observations yet.')
                except Exception as exc:st.warning(f'History unavailable: {type(exc).__name__}')
            else:st.caption('A shared exact product identifier is needed for price history.')
        st.caption('Retailer scores are illustrative. Missing shipping fees, tax, optional protection plans and membership costs are NOT assumed to be free. Rankings do not depend on affiliate commissions.')
else:
    st.info('Enter a product and compare live Google Shopping listings.' if live else 'Configure your SerpApi key to start searching live listings.')
