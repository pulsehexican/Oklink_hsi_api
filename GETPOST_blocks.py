from web3 import Web3
from dotenv import load_dotenv
from solcx import compile_source
load_dotenv()
import time
import os
import datetime
import json
from datetime import datetime, timedelta
from playsound import playsound
import requests
import contracts as contracts
import keys as keys

####################################################################################
####                            Declarations
####################################################################################

account_address = keys.account_address
account_private_key = keys.account_private_key

Blockchain="ethf"

if Blockchain=="ethw":
	w3 = Web3(Web3.HTTPProvider('https://mainnet.ethereumpow.org'))
	URL = 'https://www.oklink.com/en/ethw'
elif Blockchain=="ethf":
	w3 = Web3(Web3.HTTPProvider('https://rpc.etherfair.org/'))
	URL = 'https://www.oklink.com/en/ethf'

OwnerAddress = '0xfc4913214444aF5c715cc9F7b52655e788A569ed'

#print("build hedron contract")
hedron_contract = w3.eth.contract(address = contracts.hedron_address , abi = contracts.abi_hedron)
#print("build hsi contract")
hsi_contract = w3.eth.contract(address = contracts.hsi_address, abi = contracts.abi_hsi)
#print("build hex contract")
hex_contract = w3.eth.contract(address = contracts.hex_address, abi = contracts.abi_hex)

testmode = True

# defining the api-endpoint 
API_ENDPOINT = "https://www.oklink.com/"

# your API key here
API_KEY = ""

current_hedron_day=hedron_contract.functions.currentDay().call()
current_hex_day=hex_contract.functions.currentDay().call()

HSIaddressTab=[]

####################################################################################
####                            Functions
####################################################################################

def current_hedron_time_in_days():
    dt = datetime.now()
    my_date = dt 
    hedron_hour=my_date.hour-1
    calculation=current_hedron_day*24*60*60*60
    if hedron_hour<0:
        calculation1=(23*60*60*60)+(my_date.minute*60*60)+(my_date.second*60)+my_date.microsecond/1000000
    else:
        calculation1=(hedron_hour*60*60*60)+(my_date.minute*60*60)+(my_date.second*60)+my_date.microsecond/1000000
    calculation_result=calculation+calculation1
    return(calculation_result/(24*60*60*60))

def check_if_hsi_is_ready_for_liquidation(loan_day):
    return(current_hedron_day-loan_day)

def ShareListPrint(HSIaddress,ShareList):
    #print(ShareList)
    #stake,
    #uint16(mintedDays),
    #uint8(launchBonus),
    #uint16(loanStart),
    #uint16(loanedDays),
    #uint32(interestRate),
    #uint8(paymentsMade),
    #isLoaned
    print("HSIaddress:",HSIaddress)
    print("stake_id:",ShareList[0][0])
    print("T-shares:",round(ShareList[0][1]/1000000000000,2))
    print("stake start on hex day:",ShareList[0][2])
    print("stake days:",ShareList[0][3])
    print("Hedron minted on day:",ShareList[1])
    if ShareList[2]/10<1:
        print("Hedron bonus:",round(ShareList[2]/10,0))
    else:
        print("Hedron bonus > 0 !!!!!!!!!!!!!!!!!!!!!:",round(ShareList[2]/10,0))
    print("Loan start on hedron day:",ShareList[3])
    print("interest rate:",ShareList[5])
    print("payments made:",ShareList[6])
    print("is loaned:",ShareList[7])
    if ShareList[7]==True and check_if_hsi_is_ready_for_liquidation(ShareList[3])>=90:
        print("HSI is ready for liquidation !!!!!!!!!")
    elif ShareList[7]==True and check_if_hsi_is_ready_for_liquidation(ShareList[3])<90:
        print("HSI will be ready for liquidation in days:",90-check_if_hsi_is_ready_for_liquidation(ShareList[3]))
    else:
        print("HSI not ready for liquidation")
    # Data to be written to file
    sharelistF = {
		"HSIaddress":HSIaddress,
		"stake_id":ShareList[0][0],
		"T-shares:":round(ShareList[0][1]/1000000000000,2),
		"stake start on hex day:":ShareList[0][2],
		"stake days:":ShareList[0][3],
		"Hedron minted on day":ShareList[1],
		"Hedron bonus:":round(ShareList[2]/10,0),
		"Loan start on hedron day:":ShareList[3],
		"Is Loaned:":ShareList[7]
	}
    json_object = json.dumps(sharelistF, indent=9)
    with open("sharelist_160922.json", "a") as outfile:
        outfile.write(json_object)
        #json.dumps(json_object, outfile)



def get_hsi_data_from_tx(tx):
	HSIaddressTabLocal={}
	try:
		tx1_receipt = w3.eth.get_transaction_receipt(tx)
		print("found hexStakeSell function")
		#this is the proper HSI number i figured out in the sell function. has some several (not many) exceptions i have to debug them later
		HSIaddress=tx1_receipt.logs[5].topics[2].hex()
		#print(HSIaddress)
		addr1=str(HSIaddress.replace('0x000000000000000000000000','0x'))
		#print(addr1)
		stakeLists1=hex_contract.functions.stakeLists(Web3.toChecksumAddress(addr1),0).call()
		#print(stakeLists1)
		stake_id=stakeLists1[0]
		#print(stake_id)
		shareLists1=hedron_contract.functions.shareList(stake_id).call()
		ShareListPrint(addr1,shareLists1)
		if shareLists1[7]==True and check_if_hsi_is_ready_for_liquidation(shareLists1[3])>=90 :
			Stake_id=shareLists1[0][0]
			B_shares=shareLists1[0][1]/1000000000
			Hex_stake_start_day=shareLists1[0][2]
			Hedron_mint_day=shareLists1[1]
			Loan_start_on_hedron_day=shareLists1[3]
			Stake_length=shareLists1[0][3]
			Mintable_hedron=round((current_hex_day-Hex_stake_start_day)*B_shares,2)-round(Hedron_mint_day*B_shares,2)
			Hedron_bonus=int(shareLists1[2]/10)
			HSIaddressTabLocal={'HSI_address:':addr1,
								'Stake_id:':Stake_id,
								'HSI_index:':0,#cannot fetch from the contract read, tx decoding on ETHW/F doesn't work also. needed for liquidation start.
								'T-shares:':round(B_shares/1000,2),
								'Stake_length:':Stake_length,
								'Stake_start:':Hex_stake_start_day,
								'Hedron_mint_day:':Hedron_mint_day,
								'Hedron_bonus:':Hedron_bonus,
								'Loan_start_on_hedron_day:':Loan_start_on_hedron_day,
								'Is_loaned:':shareLists1[7],
								'Mintable_hedron:':Mintable_hedron+(Mintable_hedron*Hedron_bonus),
								'Min_bid:':round(B_shares*Stake_length+Mintable_hedron,2)#still not 100% accurate. has to be updated with the case that someone took a loan, paid several times and the hsi went to liquidation. 								
							   }
		print("-------------------------------------------------------------------------------")
	except Exception as err:
		print("exception error : ",err)
	print(HSIaddressTabLocal)
	return(HSIaddressTabLocal)


####################################################################################
####                            Script code
####################################################################################


url = "https://www.oklink.com/api/v5/explorer/address/transaction-list?chainShortName=" +Blockchain+ "&address=0xfc4913214444aF5c715cc9F7b52655e788A569ed&protocolType=token_721&limit=50"
headers = {'Ok-Access-Key': '{key}'.format(key=API_KEY)}
jsonData = requests.get(url, headers=headers).json()

total_pages=int(jsonData.get('data')[0].get('totalPage'))
print("total pages of hexStakeSell function on ",Blockchain," : ",total_pages)

#somehow the oklink api has a bug and returns always 2 the same transactions in a row :/ thats why I had to compare the transactions one by another to avoid data duplication
tx2=''
tx1='null'

url1 = "https://www.oklink.com/api/v5/explorer/address/transaction-list?chainShortName=" +Blockchain+ "&address=0xfc4913214444aF5c715cc9F7b52655e788A569ed&protocolType=token_721&limit=50&page="

#iterate through the pages of transactions HSI stake sell
for page_no in range(total_pages,1,-1):
	url=url1+str(page_no)
	headers = {'Ok-Access-Key': '{key}'.format(key=API_KEY)}
	jsonData = requests.get(url, headers=headers).json()
	
	transactions = jsonData.get('data')[0].get('transactionLists')
	#iterate through the 0x8a06a50c methods - hexStakeSell function of token 721 on the hsi contract 0xfc4913214444aF5c715cc9F7b52655e788A569ed
	for tx in transactions:
		tx1=tx.get('txId')
		methodId=tx.get('methodId')
		if tx2!=tx1 and methodId=="0x8a06a50c":
			print("tx number:", tx1)
			tx2=tx1
			HSIdata=get_hsi_data_from_tx(tx1)
			if HSIdata :
				HSIaddressTab.append(HSIdata)
print("page:",page_no," summary :")
for x in HSIaddressTab:
	print(x)
print("-------------------------------------------------------------------------------")
print("-------------------------------------------------------------------------------")
print("-------------------------------------------------------------------------------")
	
print("final address tab")
for x in HSIaddressTab:
	print(x)

print("end")





