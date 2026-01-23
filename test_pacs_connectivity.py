#!/usr/bin/env python3
"""
Test PACS connectivity from the container
"""
import socket
import sys

def test_tcp_connection(host, port, timeout=5):
    """Test if we can connect to host:port"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()

        if result == 0:
            print(f"✓ SUCCESS: Can connect to {host}:{port}")
            return True
        else:
            print(f"✗ FAILED: Cannot connect to {host}:{port} (error code: {result})")
            return False
    except socket.gaierror as e:
        print(f"✗ FAILED: DNS resolution failed for {host}: {e}")
        return False
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False

def test_dicom_echo(host, port, ae_title="ANY-SCP", calling_ae="D2D_SCU"):
    """Test DICOM C-ECHO"""
    try:
        from pynetdicom import AE
        from pynetdicom.sop_class import VerificationSOPClass

        ae = AE()
        ae.add_requested_context(VerificationSOPClass)
        ae.ae_title = calling_ae

        print(f"\nAttempting DICOM C-ECHO to {host}:{port}")
        print(f"  Calling AE: {calling_ae}")
        print(f"  Called AE: {ae_title}")

        assoc = ae.associate(host, port, ae_title=ae_title)

        if assoc.is_established:
            print("  ✓ Association established")
            status = assoc.send_c_echo()
            assoc.release()

            if status:
                print(f"  ✓ C-ECHO successful (status: {status.Status})")
                return True
            else:
                print(f"  ✗ C-ECHO failed")
                return False
        else:
            print(f"  ✗ Association rejected")
            return False

    except ImportError:
        print("  ⚠ pynetdicom not installed, skipping DICOM test")
        return None
    except Exception as e:
        print(f"  ✗ DICOM C-ECHO failed: {e}")
        return False

if __name__ == "__main__":
    # Test PACS connectivity
    pacs_host = "10.17.1.21"
    pacs_port = 5000

    print("=" * 60)
    print("PACS Connectivity Test")
    print("=" * 60)
    print(f"Target: {pacs_host}:{pacs_port}\n")

    # Test 1: TCP connectivity
    print("Test 1: TCP Socket Connection")
    print("-" * 60)
    tcp_ok = test_tcp_connection(pacs_host, pacs_port)

    # Test 2: DICOM C-ECHO
    print("\nTest 2: DICOM C-ECHO")
    print("-" * 60)
    dicom_ok = test_dicom_echo(pacs_host, pacs_port)

    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  TCP Connection: {'✓ PASS' if tcp_ok else '✗ FAIL'}")
    if dicom_ok is not None:
        print(f"  DICOM C-ECHO:   {'✓ PASS' if dicom_ok else '✗ FAIL'}")
    else:
        print(f"  DICOM C-ECHO:   ⚠ SKIPPED")
    print("=" * 60)

    sys.exit(0 if tcp_ok else 1)
