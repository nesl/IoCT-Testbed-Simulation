#include <iostream>
#include <string>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <unordered_map>
#include <chrono>
#include <queue>
#include <deque>
#include "stdlib.h"
#include <PcapLiveDeviceList.h>
#include "SystemUtils.h"
#include <PcapLiveDevice.h>
#include <IPv4Layer.h>
#include <EthLayer.h>
#include <Packet.h>
#include <PcapFilter.h>
// #include <boost/interprocess/managed_shared_memory.hpp>
// #include <boost/interprocess/containers/string.hpp>
// #include <boost/interprocess/containers/map.hpp>
// #include <boost/interprocess/allocators/allocator.hpp>

using namespace std;


#define LATDEBUG 1


// // Shared memory abstraction for latencies
// typedef boost::interprocess::allocator<char, boost::interprocess::managed_shared_memory::segment_manager> CharAllocator;
// typedef basic_string<char, char_traits<char>, CharAllocator> MyString;
// typedef double MyType;
// typedef std::pair<const MyString, MyType> ValueType;
// typedef boost::interprocess::allocator<ValueType, boost::interprocess::managed_shared_memory::segment_manager> ShmemAllocator;
// typedef map<MyString, MyType, less<MyString>, ShmemAllocator> MyMap;


template <typename T, int MaxLen, typename Container=std::deque<T>>
class FixedQueue : public std::queue<T, Container> {
public:
    void push(const T& value) {
        if (this->size() == MaxLen) {
           this->c.pop_front();
        }
        queue<T, Container>::push(value);
    }


	// Get the average of all elements in the queue
	void get_average() {

		double total_lat(0);
		int total_num = 0;

		while (!this->empty())
		{
			total_lat += this->front().count();
			total_num++;
			this->pop();
		}

		// Print output
		cout << "Duration: " << total_lat / total_num << endl;

	}

};

// Code for reading from arp table
string GetMacAddressFromARPTable(string ipAddress) {
    ifstream arpFile("/proc/net/arp");
    if (!arpFile.is_open()) {
        return "Error opening ARP table";
    }

    // Skip the first line (header)
    string line;
    getline(arpFile, line);

    // Read the ARP table line by line
    while (getline(arpFile, line)) {
        istringstream iss(line);
        string ip, hwType, flags, hwAddress, mask, device;
        iss >> ip >> hwType >> flags >> hwAddress >> mask >> device;

        if (ip == ipAddress) {
            return hwAddress;
        }
    }

    return "Not found";
}


struct LinkData
{

	
	// Create or open the shared memory segment
    // boost::interprocess::managed_shared_memory segment(boost::interprocess::open_or_create, "SharedMemory", 1024);

    // Allocate memory for the hash table
	// ShmemAllocator alloc_inst;
    //const ShmemAllocator alloc_inst (segment.get_segment_manager());
    //MyMap *myMap = segment.construct<MyMap>("MyMap")(less<MyString>(), alloc_inst);

    string host_intf;
	string veth_intf;
	string real_ip;
	string mininet_ip;
	// boost::interprocess::managed_shared_memory segment;
	// MyMap *myMap;
	pcpp::PcapLiveDevice* host_dev;
	pcpp::PcapLiveDevice* mininet_dev;

	FixedQueue<chrono::duration<double>, 100> forward_in_latency;
	FixedQueue<chrono::duration<double>, 100> forward_out_latency;
	

	LinkData(string host_intf, string veth_intf, string real_ip, string mininet_ip, 
			pcpp::PcapLiveDevice* host_dev, pcpp::PcapLiveDevice* mininet_dev) 
	{ 
		this->host_intf = host_intf;
		this->veth_intf = veth_intf;
		this->real_ip = real_ip;
		this->mininet_ip = mininet_ip;
		this->host_dev = host_dev;
		this->mininet_dev = mininet_dev;

		// using namespace boost::interprocess;
		// this->segment = managed_shared_memory(open_or_create, "SharedMemory", 1024 );
		// // Allocate memory for the hash table
		// ShmemAllocator alloc_inst(this->segment.get_segment_manager());
		// myMap = segment.construct<MyMap>("MyMap")(std::less<MyString>(), alloc_inst);

	}

	void removeSharedMemory() {
		//boost::interprocess::shared_memory_object::remove("SharedMemory");
		return;
	}

	void displayData() {
		cout << "host_intf: " << host_intf << endl;
		cout << "veth_intf: " << veth_intf << endl;
		cout << "real_ip: " << real_ip << endl;
		cout << "mininet_ip: " << mininet_ip << endl;
	}

	void appendToInLatency(chrono::duration<double> in_lat) {
		forward_in_latency.push(in_lat);
	}

	void appendToOutLatency(chrono::duration<double> out_lat) {
		forward_out_latency.push(out_lat);
	}

	string get_realip() {
		return real_ip;
	}

	string get_hostintf() {
		return host_intf;
	}

	pcpp::PcapLiveDevice* get_hostdev() {
		return host_dev;
	}

	pcpp::PcapLiveDevice* get_mininetdev() {
		return mininet_dev;
	}

	void displayLatencies() {
		cout << "In latency: " << endl;
		forward_in_latency.get_average();
		cout << "Out Latency: " << endl;
		forward_out_latency.get_average();
	}

};


// Handle forwarding to mininet
// Let's say the real address of this device is 10.0.0.11
//  Then this will read in packets coming from 10.0.0.11
//  And then later forward them to the destination device.

static void forward_to_mininet(pcpp::RawPacket* packet, \
	pcpp::PcapLiveDevice* dev, void* metadata) {

	// TIMING: start time forward to external
	const auto start{chrono::steady_clock::now()};

	// Get the metadata
	LinkData* link_metadata = (LinkData*)metadata;
	// link_metadata->displayData();

	// parsed the raw packet
    pcpp::Packet parsedPacket(packet);

	cout << parsedPacket.toString();

	// Send on the mininet interface
	if (!link_metadata->get_mininetdev()->sendPacket(*packet)) {
		cerr << "Failed to send packet to mininet!" << endl;
		return;
	}
	else {
		cout << "sent packet to mininet!" << endl;

		// TIMING: Add packet ID to shared hash table
		//   and the current time.

	}

	

	#if LATDEBUG == 1
		// TIMING: end time forward to external
		const auto end{chrono::steady_clock::now()};
		chrono::duration<double> elapsed_seconds{end - start};
		link_metadata->appendToInLatency(elapsed_seconds);
	#endif
}

// This listens for packets which are being sent to the given IP address
//  Note that the forward to mininet and forward to external are not expecting
//  the same packets (they handle separate flows of communication).
static void forward_to_external(pcpp::RawPacket* packet, \
	pcpp::PcapLiveDevice* dev, void* metadata) {

	// TIMING: start time forward to external
	const auto start{chrono::steady_clock::now()};

	// TIMING: Check packet ID, match against hash table, and 
	//   calcalate difference with the current time.

	// Get the metadata
	LinkData* link_metadata = (LinkData*)metadata;
	// link_metadata->displayData();

	// parsed the raw packet
    pcpp::Packet parsedPacket(packet);

	// cout << "Received packet!" << endl;
	// cout << parsedPacket.toString();

	// Get layer 2 information
	pcpp::MacAddress orig_destMAC = parsedPacket.getLayerOfType<pcpp::EthLayer>()->getDestMac();
	const string realMACaddr = GetMacAddressFromARPTable(link_metadata->get_realip());
	pcpp::MacAddress realmac(realMACaddr);
	parsedPacket.getLayerOfType<pcpp::EthLayer>()->setDestMac(realmac);
	parsedPacket.getLayerOfType<pcpp::EthLayer>()->setSourceMac(orig_destMAC);

	// Only send the raw packet (payload), without ethernet frames
	// parsedPacket.removeFirstLayer();

	cout << parsedPacket.toString();

	// Send on the external interface
	if (!link_metadata->get_hostdev()->sendPacket(&parsedPacket)) {
		cerr << "Failed to send packet to external!" << endl;
		return;
	}
	else {
		cout << "sent packet to external!" << endl;




	}

	
	#if LATDEBUG == 1
		// TIMING: end time forward to external
		const auto end{chrono::steady_clock::now()};
		chrono::duration<double> elapsed_seconds{end - start};
		link_metadata->appendToOutLatency(elapsed_seconds);
	#endif
}


int main(int argc, char* argv[])
{
	// Make sure we get the correct number of arguments
	if (argc != 5) {
		cerr << "Incorrect number of arguments." << endl;
		return -1;
	}

	// Parse the arguments
	string veth_intf(argv[1]);
	string host_intf(argv[2]);
	string mininet_addr(argv[3]);
	string real_addr(argv[4]);


	
	// const vector<PcapLiveDevice *>& devices = pcpp::PcapLiveDeviceList::getInstance().getPcapLiveDevicesList();
	// cout << pcpp::PcapLiveDeviceList::getInstance().getPcapLiveDevicesList();

	// Now, get the device
	// find the interface by IP address
	pcpp::PcapLiveDevice* host_dev = pcpp::PcapLiveDeviceList::getInstance().getPcapLiveDeviceByName(host_intf);
	if (host_dev == NULL)
	{
		std::cerr << "Cannot find interface with name of '" << host_intf << "'" << std::endl;
		return 1;
	}
	pcpp::PcapLiveDevice* mininet_dev = pcpp::PcapLiveDeviceList::getInstance().getPcapLiveDeviceByName(veth_intf);
	if (mininet_dev == NULL)
	{
		std::cerr << "Cannot find interface with name of '" << veth_intf << "'" << std::endl;
		return 1;
	}

	// Open both the host and mininet dev
	if (!(host_dev->open() && mininet_dev->open())) {
		std::cerr << "Failed to open both interfaces..." << endl;
		return 1;
	}

	// Add filters to our host device
	pcpp::IPFilter filter_in_1(real_addr, pcpp::Direction::SRC);
	pcpp::MacAddressFilter filter_in_2(host_dev->getMacAddress(), pcpp::Direction::SRC);
	pcpp::NotFilter filter_in_3(&filter_in_2);
	pcpp::AndFilter filter_in;
	filter_in.addFilter(&filter_in_1);
	filter_in.addFilter(&filter_in_3);
	host_dev->setFilter(filter_in);

	// Add filters to our mininet device
	pcpp::IPFilter filter_out_1(mininet_addr, pcpp::Direction::DST);
	mininet_dev->setFilter(filter_out_1);

	// Save some link data
	LinkData link_metadata(host_intf, veth_intf, real_addr, mininet_addr, host_dev, mininet_dev);


	// Open the device and begin capturing
	cout << "Open" << endl;
	host_dev->startCapture(forward_to_mininet, &link_metadata);
	mininet_dev->startCapture(forward_to_external, &link_metadata);
	// sleep for X seconds in main thread, in the meantime packets are captured in the async thread
	pcpp::multiPlatformSleep(10);
	// stop capturing packets
	host_dev->stopCapture();
	mininet_dev->stopCapture();
	
	cout << "Displaying Latencies: " << endl;
	// Now print out our link latencies
	link_metadata.displayLatencies();
	// link_metadata.removeSharedMemory();
	


	return 0;
}
