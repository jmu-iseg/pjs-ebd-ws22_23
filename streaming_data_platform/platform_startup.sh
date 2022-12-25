python server_output.py &
python server_bConsum.py &
python server_mConsum.py &
python server_pConsum.py &
sleep 10s
python client_producer_output.py &
python client_producer_bConsum.py &
python client_producer_mConsum.py &
python client_producer_pConsum.py &